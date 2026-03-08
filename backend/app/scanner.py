import json
import logging
import math
import time
from datetime import date, datetime
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf
from sqlalchemy.orm import Session

from app.config import MIN_MARKET_CAP, MIN_AVG_VOLUME
from app.models import StockSignal
from app.rating import rate_signal
from app.tickers import fetch_all_us_tickers
from app.yf_session import session as yf_session

logger = logging.getLogger(__name__)

BATCH_SIZE = 200
HISTORY_PERIOD = "8mo"
SMA_WINDOW = 30
RATE_LIMIT_THRESHOLD = 8
INFO_DELAY = 0.6
INFO_RETRY_DELAY = 3.0
INFO_MAX_RETRIES = 2


def _safe_val(v, default=0):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return default
    return v


async def run_scan(db: Session) -> list[StockSignal]:
    """Main scan: find stocks that crossed above or below their 30-day SMA."""
    tickers = await fetch_all_us_tickers()
    if not tickers:
        logger.error("No tickers available, aborting scan")
        return []

    logger.info("Starting SMA30 crossover scan for %d tickers", len(tickers))
    crossover_tickers = _find_crossovers(tickers)
    logger.info("Found %d crossover candidates", len(crossover_tickers))

    if not crossover_tickers:
        return []

    signals = _enrich_and_filter(crossover_tickers, db)
    logger.info("After enrichment: %d qualifying stocks", len(signals))
    return signals


def _find_crossovers(tickers: list[str]) -> dict[str, dict]:
    """Download price data in batches and detect SMA 30 crossovers."""
    crossovers: dict[str, dict] = {}

    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i : i + BATCH_SIZE]
        logger.info(
            "Downloading batch %d/%d (%d tickers)",
            i // BATCH_SIZE + 1,
            (len(tickers) + BATCH_SIZE - 1) // BATCH_SIZE,
            len(batch),
        )

        try:
            data = yf.download(
                batch,
                period=HISTORY_PERIOD,
                interval="1d",
                group_by="ticker",
                threads=True,
                progress=False,
                session=yf_session,
            )
        except Exception:
            logger.exception("Failed to download batch starting at index %d", i)
            continue

        if data.empty:
            continue

        for ticker in batch:
            try:
                if len(batch) == 1:
                    close = data["Close"]
                    volume = data["Volume"]
                    open_ = data["Open"]
                    high = data["High"]
                    low = data["Low"]
                else:
                    close = data[(ticker, "Close")]
                    volume = data[(ticker, "Volume")]
                    open_ = data[(ticker, "Open")]
                    high = data[(ticker, "High")]
                    low = data[(ticker, "Low")]

                close = close.dropna()
                if len(close) < SMA_WINDOW + 2:
                    continue

                sma = close.rolling(window=SMA_WINDOW).mean()

                today_close = close.iloc[-1]
                yesterday_close = close.iloc[-2]
                today_sma = sma.iloc[-1]
                yesterday_sma = sma.iloc[-2]

                if pd.isna(today_sma) or pd.isna(yesterday_sma):
                    continue

                crossed_above = (
                    today_close > today_sma and yesterday_close <= yesterday_sma
                )
                crossed_below = (
                    today_close < today_sma and yesterday_close >= yesterday_sma
                )

                if crossed_above or crossed_below:
                    avg_vol = volume.tail(30).mean()
                    tail_idx = close.tail(60).index
                    history = []
                    for ts in tail_idx:
                        t = int(pd.Timestamp(ts).timestamp())
                        c = round(float(close.get(ts, 0)), 2)
                        o = round(float(open_.get(ts, c)), 2)
                        h = round(float(high.get(ts, c)), 2)
                        l = round(float(low.get(ts, c)), 2)
                        sma_val = sma.get(ts)
                        history.append(
                            {
                                "time": t,
                                "value": c,
                                "open": o,
                                "high": h,
                                "low": l,
                                "close": c,
                                "sma": round(float(sma_val), 2)
                                if sma_val and not pd.isna(sma_val)
                                else None,
                            }
                        )

                    w_sma30 = None
                    w_above = None
                    try:
                        weekly_close = close.resample("W").last().dropna()
                        if len(weekly_close) >= SMA_WINDOW:
                            w_sma = weekly_close.rolling(window=SMA_WINDOW).mean()
                            latest_w_sma = w_sma.iloc[-1]
                            if not pd.isna(latest_w_sma):
                                w_sma30 = round(float(latest_w_sma), 2)
                                w_above = float(today_close) > w_sma30
                    except Exception:
                        pass

                    crossovers[ticker] = {
                        "price": float(today_close),
                        "sma30": float(today_sma),
                        "weekly_sma30": w_sma30,
                        "above_weekly_sma": w_above,
                        "avg_volume": int(_safe_val(avg_vol)),
                        "crossover_date": close.index[-1].date(),
                        "price_history": history,
                        "signal_type": "bullish" if crossed_above else "bearish",
                    }
            except Exception:
                continue

    return crossovers


def _fetch_info(ticker: str) -> Optional[dict]:
    """Fetch ticker info with retries on rate-limit errors."""
    for attempt in range(INFO_MAX_RETRIES + 1):
        try:
            info = yf.Ticker(ticker, session=yf_session).info
            if info and info.get("regularMarketPrice"):
                return info
            return None
        except Exception as e:
            err_str = str(e).lower()
            if "rate" in err_str or "too many" in err_str:
                if attempt < INFO_MAX_RETRIES:
                    wait = INFO_RETRY_DELAY * (attempt + 1)
                    logger.debug("Rate limited on %s, waiting %.1fs (attempt %d)", ticker, wait, attempt + 1)
                    time.sleep(wait)
                    continue
            return None
    return None


def _build_fundamentals_cache(db: Session) -> dict[str, dict]:
    """Load previously-stored fundamentals so we don't need to re-fetch."""
    cache: dict[str, dict] = {}
    for sig in db.query(StockSignal).all():
        cache[sig.ticker] = {
            "company_name": sig.company_name,
            "sector": sig.sector,
            "industry": sig.industry,
            "market_cap": sig.market_cap,
            "revenue": sig.revenue,
            "pe_ratio": sig.pe_ratio,
            "revenue_growth": sig.revenue_growth,
            "operating_margin": sig.operating_margin,
            "operating_cashflow": sig.operating_cashflow,
            "free_cashflow": sig.free_cashflow,
            "ps_ratio": sig.ps_ratio,
            "pb_ratio": sig.pb_ratio,
            "avg_volume": sig.avg_volume,
        }
    return cache


MIN_REVENUE = 100_000_000  # $100M


def _passes_hard_filter(
    revenue: int,
    operating_margin: Optional[float],
    operating_cashflow: int,
    free_cashflow: int,
) -> bool:
    """Reject structurally low-quality stocks from the main scan."""
    if revenue < MIN_REVENUE:
        return False
    if operating_margin is not None and operating_margin < 0 and revenue < 1_000_000_000:
        return False
    if operating_cashflow < 0 and free_cashflow < 0:
        return False
    return True


def _enrich_and_filter(
    crossovers: dict[str, dict], db: Session
) -> list[StockSignal]:
    """Fetch fundamentals for crossover candidates and apply filters."""
    signals: list[StockSignal] = []
    cached_fundamentals = _build_fundamentals_cache(db)

    candidates = {
        t: d for t, d in crossovers.items()
        if d["avg_volume"] >= MIN_AVG_VOLUME
    }
    logger.info("After volume pre-filter: %d of %d candidates", len(candidates), len(crossovers))

    consecutive_failures = 0
    total_fetched = 0
    total_cached = 0

    for idx, (ticker, data) in enumerate(candidates.items()):
        info = None

        if consecutive_failures < RATE_LIMIT_THRESHOLD:
            if idx > 0:
                time.sleep(INFO_DELAY)
            info = _fetch_info(ticker)

            if info is None:
                consecutive_failures += 1
                if consecutive_failures >= RATE_LIMIT_THRESHOLD:
                    logger.warning(
                        "Hit %d consecutive failures at candidate %d/%d — "
                        "pausing for 30s then resuming",
                        consecutive_failures, idx + 1, len(candidates),
                    )
                    time.sleep(30)
                    consecutive_failures = 0
            else:
                consecutive_failures = 0
                total_fetched += 1
        else:
            total_cached += 1

        if info:
            market_cap = _safe_val(info.get("marketCap"))
            avg_volume = _safe_val(info.get("averageVolume", data["avg_volume"]))
            revenue = _safe_val(info.get("totalRevenue"))
            pe_ratio = info.get("trailingPE")
            revenue_growth = info.get("revenueGrowth")
            operating_margin = info.get("operatingMargins")
            operating_cashflow = _safe_val(info.get("operatingCashflow"))
            free_cashflow = _safe_val(info.get("freeCashflow"))
            ps_ratio = info.get("priceToSalesTrailing12Months")
            pb_ratio = info.get("priceToBook")
            company_name = info.get("shortName", info.get("longName", ticker))
            sector = info.get("sector", "")
            industry = info.get("industry", "")

            if market_cap < MIN_MARKET_CAP:
                continue

            if not _passes_hard_filter(revenue, operating_margin, operating_cashflow, free_cashflow):
                logger.debug("Hard filter rejected %s", ticker)
                continue

            cached_fundamentals[ticker] = {
                "company_name": company_name,
                "sector": sector,
                "industry": industry,
                "market_cap": market_cap,
                "revenue": revenue,
                "pe_ratio": pe_ratio,
                "revenue_growth": revenue_growth,
                "operating_margin": operating_margin,
                "operating_cashflow": operating_cashflow,
                "free_cashflow": free_cashflow,
                "ps_ratio": ps_ratio,
                "pb_ratio": pb_ratio,
                "avg_volume": avg_volume,
            }
        elif ticker in cached_fundamentals:
            f = cached_fundamentals[ticker]
            market_cap = f["market_cap"]
            avg_volume = f["avg_volume"]
            revenue = f["revenue"]
            pe_ratio = f["pe_ratio"]
            revenue_growth = f.get("revenue_growth")
            operating_margin = f.get("operating_margin")
            operating_cashflow = f.get("operating_cashflow", 0)
            free_cashflow = f.get("free_cashflow", 0)
            ps_ratio = f.get("ps_ratio")
            pb_ratio = f.get("pb_ratio")
            company_name = f["company_name"]
            sector = f["sector"]
            industry = f["industry"]

            if market_cap < MIN_MARKET_CAP:
                continue
        else:
            continue

        news: list[dict] = []
        if info:
            news = _fetch_news(ticker)

        result = rate_signal(
            price=data["price"],
            sma30=data["sma30"],
            market_cap=market_cap,
            revenue=revenue,
            pe_ratio=pe_ratio,
            avg_volume=avg_volume,
            revenue_growth=revenue_growth,
            operating_margin=operating_margin,
            free_cashflow=free_cashflow,
            ps_ratio=ps_ratio,
        )

        sig_type = data.get("signal_type", "bullish")

        existing = (
            db.query(StockSignal)
            .filter(
                StockSignal.ticker == ticker,
                StockSignal.crossover_date == data["crossover_date"],
            )
            .first()
        )
        if existing:
            existing.current_price = data["price"]
            existing.price_change_pct = round(
                (data["price"] - existing.price_at_crossover)
                / existing.price_at_crossover
                * 100,
                2,
            ) if existing.price_at_crossover else 0
            existing.signal_type = sig_type
            existing.rating = result.stars
            existing.rating_reasons = result.to_list()
            existing.revenue_growth = revenue_growth
            existing.operating_margin = operating_margin
            existing.operating_cashflow = operating_cashflow
            existing.free_cashflow = free_cashflow
            existing.ps_ratio = ps_ratio
            existing.pb_ratio = pb_ratio
            existing.weekly_sma30 = data.get("weekly_sma30")
            existing.above_weekly_sma = data.get("above_weekly_sma")
            if news:
                existing.news = news
            existing.price_history = data["price_history"]
            existing.updated_at = datetime.utcnow()
            signals.append(existing)
            continue

        signal = StockSignal(
            ticker=ticker,
            company_name=company_name,
            sector=sector,
            industry=industry,
            market_cap=market_cap,
            revenue=revenue,
            pe_ratio=pe_ratio,
            revenue_growth=revenue_growth,
            operating_margin=operating_margin,
            operating_cashflow=operating_cashflow,
            free_cashflow=free_cashflow,
            ps_ratio=ps_ratio,
            pb_ratio=pb_ratio,
            avg_volume=avg_volume,
            price_at_crossover=data["price"],
            sma30_at_crossover=data["sma30"],
            weekly_sma30=data.get("weekly_sma30"),
            above_weekly_sma=data.get("above_weekly_sma"),
            crossover_date=data["crossover_date"],
            current_price=data["price"],
            price_change_pct=0.0,
            signal_type=sig_type,
            rating=result.stars,
            rating_reasons_json=json.dumps(result.to_list()),
            news_json=json.dumps(news),
            price_history_json=json.dumps(data["price_history"]),
        )
        db.add(signal)
        signals.append(signal)

    db.commit()
    logger.info("Enrichment done: %d fresh fetches, %d from cache", total_fetched, total_cached)
    return signals


def backfill_ohlc(db: Session):
    """Backfill OHLC data for stocks that were saved before OHLC extraction."""
    signals = db.query(StockSignal).all()
    need_backfill = [s for s in signals if '"open"' not in s.price_history_json]
    if not need_backfill:
        logger.info("All stocks already have OHLC data, nothing to backfill")
        return

    tickers = [s.ticker for s in need_backfill]
    logger.info("Backfilling OHLC for %d stocks: %s", len(tickers), tickers[:10])

    ticker_to_signal = {s.ticker: s for s in need_backfill}

    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i : i + BATCH_SIZE]
        try:
            data = yf.download(
                batch,
                period=HISTORY_PERIOD,
                interval="1d",
                group_by="ticker",
                threads=True,
                progress=False,
                session=yf_session,
            )
        except Exception:
            logger.exception("Backfill: failed to download batch at index %d", i)
            continue

        if data.empty:
            continue

        for ticker in batch:
            try:
                if len(batch) == 1:
                    close = data["Close"]
                    open_ = data["Open"]
                    high = data["High"]
                    low = data["Low"]
                else:
                    close = data[(ticker, "Close")]
                    open_ = data[(ticker, "Open")]
                    high = data[(ticker, "High")]
                    low = data[(ticker, "Low")]

                close = close.dropna()
                if len(close) < 2:
                    continue

                sma = close.rolling(window=SMA_WINDOW).mean()
                tail_idx = close.tail(60).index
                history = []
                for ts in tail_idx:
                    t = int(pd.Timestamp(ts).timestamp())
                    c = round(float(close.get(ts, 0)), 2)
                    o = round(float(open_.get(ts, c)), 2)
                    h = round(float(high.get(ts, c)), 2)
                    l = round(float(low.get(ts, c)), 2)
                    sma_val = sma.get(ts)
                    history.append(
                        {
                            "time": t,
                            "value": c,
                            "open": o,
                            "high": h,
                            "low": l,
                            "close": c,
                            "sma": round(float(sma_val), 2)
                            if sma_val and not pd.isna(sma_val)
                            else None,
                        }
                    )

                sig = ticker_to_signal[ticker]
                sig.price_history = history
                sig.updated_at = datetime.utcnow()
            except Exception:
                logger.warning("Backfill: failed for %s", ticker)
                continue

    db.commit()
    logger.info("OHLC backfill complete")


def _fetch_news(ticker: str) -> list[dict]:
    """Fetch recent news headlines for a ticker."""
    try:
        t = yf.Ticker(ticker, session=yf_session)
        raw_news = t.news or []
        articles = []
        for item in raw_news[:8]:
            content = item.get("content", {})
            articles.append(
                {
                    "title": content.get("title", item.get("title", "")),
                    "url": content.get("canonicalUrl", {}).get(
                        "url", item.get("link", "")
                    ),
                    "publisher": content.get("provider", {}).get(
                        "displayName", item.get("publisher", "")
                    ),
                    "published": content.get("pubDate", item.get("providerPublishTime", "")),
                }
            )
        return articles
    except Exception:
        logger.warning("Failed to fetch news for %s", ticker)
        return []
