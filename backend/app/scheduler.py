import asyncio
import logging
import math

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import SCAN_HOUR, SCAN_MINUTE
from app.database import SessionLocal
from app.emailer import send_daily_recap, DailyRecap, RecapStock
from app.models import Subscriber, WatchlistItem, StockSignal
from app.rating import rate_signal
from app.scanner import run_scan

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def _safe(v, default=0):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return default
    return v


def _build_watchlist_recap(db) -> list[RecapStock]:
    """Fetch live data for watchlist tickers and determine SMA status."""
    import yfinance as yf
    import pandas as pd

    items = db.query(WatchlistItem).all()
    if not items:
        return []

    tickers = [item.ticker for item in items]
    ticker_names = {item.ticker: item.company_name for item in items}
    result: list[RecapStock] = []

    try:
        data = yf.download(
            tickers, period="8mo", interval="1d",
            group_by="ticker", threads=True, progress=False,
        )
    except Exception:
        logger.warning("Failed to download watchlist data for recap")
        return []

    if data.empty:
        return []

    fundamentals_cache: dict[str, dict] = {}
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info
            if info:
                fundamentals_cache[ticker] = {
                    "market_cap": _safe(info.get("marketCap")),
                    "revenue": _safe(info.get("totalRevenue")),
                    "pe_ratio": info.get("trailingPE"),
                    "revenue_growth": info.get("revenueGrowth"),
                    "operating_margin": info.get("operatingMargins"),
                    "operating_cashflow": _safe(info.get("operatingCashflow")),
                    "free_cashflow": _safe(info.get("freeCashflow")),
                    "ps_ratio": info.get("priceToSalesTrailing12Months"),
                    "avg_volume": _safe(info.get("averageVolume")),
                }
        except Exception:
            continue

    for ticker in tickers:
        try:
            if len(tickers) == 1:
                close = data["Close"].dropna()
            else:
                close = data[(ticker, "Close")].dropna()

            if len(close) < 31:
                continue

            sma30 = close.rolling(window=30).mean()
            current_price = float(close.iloc[-1])
            yesterday_price = float(close.iloc[-2])
            current_sma = float(sma30.iloc[-1]) if not pd.isna(sma30.iloc[-1]) else None
            yesterday_sma = float(sma30.iloc[-2]) if not pd.isna(sma30.iloc[-2]) else None

            if current_sma is None:
                continue

            w_sma30 = None
            w_above = None
            try:
                weekly_close = close.resample("W").last().dropna()
                if len(weekly_close) >= 30:
                    w_sma = weekly_close.rolling(window=30).mean()
                    latest_w = w_sma.iloc[-1]
                    if not pd.isna(latest_w):
                        w_sma30 = round(float(latest_w), 2)
                        w_above = current_price > w_sma30
            except Exception:
                pass

            if w_sma30 is not None:
                today_above_w = current_price > w_sma30
                yesterday_above_w = yesterday_price > w_sma30
                if today_above_w and not yesterday_above_w:
                    status = "crossed above"
                elif not today_above_w and yesterday_above_w:
                    status = "crossed below"
                elif today_above_w:
                    status = "still above"
                else:
                    status = "still below"
            else:
                today_above = current_price > current_sma
                yesterday_above = (
                    yesterday_price > yesterday_sma if yesterday_sma is not None else None
                )
                if yesterday_above is None:
                    status = "above" if today_above else "below"
                elif today_above and not yesterday_above:
                    status = "crossed above"
                elif not today_above and yesterday_above:
                    status = "crossed below"
                elif today_above:
                    status = "still above"
                else:
                    status = "still below"

            fund = fundamentals_cache.get(ticker, {})
            rating_result = rate_signal(
                price=current_price,
                sma30=current_sma,
                market_cap=fund.get("market_cap", 0),
                revenue=fund.get("revenue", 0),
                pe_ratio=fund.get("pe_ratio"),
                avg_volume=fund.get("avg_volume", 0),
                revenue_growth=fund.get("revenue_growth"),
                operating_margin=fund.get("operating_margin"),
                free_cashflow=fund.get("free_cashflow", 0),
                ps_ratio=fund.get("ps_ratio"),
            )

            result.append(RecapStock(
                ticker=ticker,
                company_name=ticker_names.get(ticker, ticker),
                price=round(current_price, 2),
                sma30=round(current_sma, 2),
                rating=rating_result.stars,
                market_cap=fund.get("market_cap", 0),
                operating_margin=fund.get("operating_margin"),
                pe_ratio=fund.get("pe_ratio"),
                weekly_sma30=w_sma30,
                above_weekly_sma=w_above,
                status=status,
            ))
        except Exception:
            continue

    return result


def _run_scheduled_scan():
    """Wrapper to run the async scan in a sync APScheduler job."""
    logger.info("Scheduled scan starting")
    db = SessionLocal()
    try:
        new_signals = asyncio.run(run_scan(db))

        top_above = []
        top_below = []
        for s in new_signals:
            stock = RecapStock(
                ticker=s.ticker,
                company_name=s.company_name,
                price=s.price_at_crossover,
                sma30=s.sma30_at_crossover,
                rating=s.rating,
                market_cap=s.market_cap,
                operating_margin=s.operating_margin,
                pe_ratio=s.pe_ratio,
                weekly_sma30=s.weekly_sma30,
                above_weekly_sma=s.above_weekly_sma,
            )
            if s.signal_type == "bullish":
                top_above.append(stock)
            else:
                top_below.append(stock)

        watchlist_stocks = _build_watchlist_recap(db)

        recap = DailyRecap(
            watchlist_stocks=watchlist_stocks,
            top_above=top_above,
            top_below=top_below,
        )

        subscribers = [
            s.email for s in db.query(Subscriber).filter(Subscriber.active).all()
        ]
        send_daily_recap(subscribers, recap)

        logger.info(
            "Scheduled scan complete: %d signals, watchlist=%d, above=%d, below=%d",
            len(new_signals), len(watchlist_stocks), len(top_above), len(top_below),
        )
    except Exception:
        logger.exception("Scheduled scan failed")
    finally:
        db.close()


def start_scheduler():
    trigger = CronTrigger(
        day_of_week="mon-fri",
        hour=SCAN_HOUR,
        minute=SCAN_MINUTE,
        timezone="US/Eastern",
    )
    scheduler.add_job(_run_scheduled_scan, trigger, id="daily_scan", replace_existing=True)
    scheduler.start()
    logger.info("Scheduler started: scan at %02d:%02d ET, Mon-Fri", SCAN_HOUR, SCAN_MINUTE)


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
