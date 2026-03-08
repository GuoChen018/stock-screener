import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.config import FRONTEND_URL
from app.database import get_db, init_db, SessionLocal
from app.yf_session import session as yf_session
from app.models import StockSignal, Subscriber, WatchlistItem, MacroTrend
from app.rating import rate_signal
from app.macro import SECTOR_ETFS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Application started")
    yield
    logger.info("Application stopped")


app = FastAPI(title="SMA30 Stock Screener", lifespan=lifespan)

_origins = ["*"]
if FRONTEND_URL:
    _origins = [FRONTEND_URL, "http://localhost:5173", "http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


class SubscribeRequest(BaseModel):
    email: EmailStr


class SubscribeResponse(BaseModel):
    message: str
    email: str


@app.get("/api/stocks")
def list_stocks(
    sector: Optional[str] = None,
    signal_type: Optional[str] = Query(None, pattern="^(bullish|bearish)$"),
    watchlist_only: bool = Query(False),
    min_market_cap: Optional[int] = None,
    max_market_cap: Optional[int] = None,
    sort_by: str = Query("rating", pattern="^(crossover_date|market_cap|price_change_pct|ticker|rating|current_price|sma30_at_crossover|avg_volume|sector|signal_type)$"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(StockSignal)

    if watchlist_only:
        wl_tickers = [t[0] for t in db.query(WatchlistItem.ticker).all()]
        query = query.filter(StockSignal.ticker.in_(wl_tickers))
    if signal_type:
        query = query.filter(StockSignal.signal_type == signal_type)
    if sector:
        query = query.filter(StockSignal.sector == sector)
    if min_market_cap is not None:
        query = query.filter(StockSignal.market_cap >= min_market_cap)
    if max_market_cap is not None:
        query = query.filter(StockSignal.market_cap <= max_market_cap)

    total = query.count()

    col = getattr(StockSignal, sort_by, StockSignal.crossover_date)
    if sort_dir == "desc":
        query = query.order_by(desc(col))
    else:
        query = query.order_by(col)

    stocks = query.offset(offset).limit(limit).all()

    return {
        "stocks": [s.to_summary() for s in stocks],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@app.get("/api/stocks/{ticker}")
def get_stock(ticker: str, db: Session = Depends(get_db)):
    import math
    import yfinance as yf
    import pandas as pd

    signal = (
        db.query(StockSignal)
        .filter(StockSignal.ticker == ticker.upper())
        .order_by(desc(StockSignal.crossover_date))
        .first()
    )
    if signal:
        return signal.to_dict()

    ticker = ticker.upper()
    try:
        t = yf.Ticker(ticker, session=yf_session)
        info = t.info or {}
        if not info.get("regularMarketPrice"):
            raise HTTPException(status_code=404, detail="Stock not found")

        def _safe(v, default=0):
            if v is None or (isinstance(v, float) and math.isnan(v)):
                return default
            return v

        hist = yf.download(ticker, period="8mo", interval="1d", progress=False, session=yf_session)
        if hist.empty:
            raise HTTPException(status_code=404, detail="No price data available")

        close = hist["Close"].dropna()
        if hasattr(close, 'columns'):
            close = close.iloc[:, 0]
        sma30 = close.rolling(window=30).mean()
        current_price = float(close.iloc[-1])
        current_sma = float(sma30.iloc[-1]) if not pd.isna(sma30.iloc[-1]) else 0.0

        w_sma30_val = None
        w_above_val = None
        try:
            weekly_close = close.resample("W").last().dropna()
            if len(weekly_close) >= 30:
                w_sma = weekly_close.rolling(window=30).mean()
                latest_w = w_sma.iloc[-1]
                if not pd.isna(latest_w):
                    w_sma30_val = round(float(latest_w), 2)
                    w_above_val = current_price > w_sma30_val
        except Exception:
            pass

        open_ = hist["Open"]
        high = hist["High"]
        low = hist["Low"]
        if hasattr(open_, 'columns'):
            open_ = open_.iloc[:, 0]
            high = high.iloc[:, 0]
            low = low.iloc[:, 0]

        tail_idx = close.tail(60).index
        price_history = []
        for ts in tail_idx:
            t_val = int(pd.Timestamp(ts).timestamp())
            c = round(float(close.get(ts, 0)), 2)
            o = round(float(open_.get(ts, c)), 2)
            h = round(float(high.get(ts, c)), 2)
            l_val = round(float(low.get(ts, c)), 2)
            sma_val = sma30.get(ts)
            price_history.append({
                "time": t_val, "value": c,
                "open": o, "high": h, "low": l_val, "close": c,
                "sma": round(float(sma_val), 2) if sma_val and not pd.isna(sma_val) else None,
            })

        revenue_growth = info.get("revenueGrowth")
        operating_margin = info.get("operatingMargins")
        operating_cashflow = _safe(info.get("operatingCashflow"))
        free_cashflow = _safe(info.get("freeCashflow"))
        ps_ratio = info.get("priceToSalesTrailing12Months")
        pb_ratio = info.get("priceToBook")
        pe_ratio = info.get("trailingPE")
        revenue = _safe(info.get("totalRevenue"))
        market_cap = _safe(info.get("marketCap"))
        avg_volume = _safe(info.get("averageVolume"))

        from app.rating import rate_signal as _rate
        result = _rate(
            price=current_price, sma30=current_sma,
            market_cap=market_cap, revenue=revenue,
            pe_ratio=pe_ratio, avg_volume=avg_volume,
            revenue_growth=revenue_growth, operating_margin=operating_margin,
            free_cashflow=free_cashflow, ps_ratio=ps_ratio,
        )

        from datetime import date as _date
        return {
            "id": 0,
            "ticker": ticker,
            "company_name": info.get("shortName", info.get("longName", ticker)),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
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
            "price_at_crossover": current_price,
            "sma30_at_crossover": current_sma,
            "weekly_sma30": w_sma30_val,
            "above_weekly_sma": w_above_val,
            "crossover_date": _date.today().isoformat(),
            "current_price": current_price,
            "price_change_pct": 0.0,
            "signal_type": "bullish" if current_price > current_sma else "bearish",
            "rating": result.stars,
            "rating_reasons": result.to_list(),
            "news": [],
            "price_history": price_history,
            "created_at": None,
            "updated_at": None,
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch live data for %s", ticker)
        raise HTTPException(status_code=404, detail="Stock not found")


@app.get("/api/stocks/{ticker}/chart")
def get_chart_data(ticker: str, db: Session = Depends(get_db)):
    signal = (
        db.query(StockSignal)
        .filter(StockSignal.ticker == ticker.upper())
        .order_by(desc(StockSignal.crossover_date))
        .first()
    )
    if not signal:
        raise HTTPException(status_code=404, detail="Stock not found")
    return {
        "ticker": signal.ticker,
        "sma30": signal.sma30_at_crossover,
        "price_history": signal.price_history,
    }


@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    total = db.query(StockSignal).count()
    sectors = (
        db.query(StockSignal.sector, func.count(StockSignal.id))
        .group_by(StockSignal.sector)
        .all()
    )
    return {
        "total_signals": total,
        "sectors": {s: c for s, c in sectors if s},
    }


@app.get("/api/sectors")
def get_sectors(db: Session = Depends(get_db)):
    sectors = (
        db.query(StockSignal.sector)
        .distinct()
        .filter(StockSignal.sector != "")
        .all()
    )
    return [s[0] for s in sectors]


@app.post("/api/subscribe", response_model=SubscribeResponse)
def subscribe(req: SubscribeRequest, db: Session = Depends(get_db)):
    existing = db.query(Subscriber).filter(Subscriber.email == req.email).first()
    if existing:
        if not existing.active:
            existing.active = True
            db.commit()
            return SubscribeResponse(message="Subscription reactivated", email=req.email)
        return SubscribeResponse(message="Already subscribed", email=req.email)

    sub = Subscriber(email=req.email)
    db.add(sub)
    db.commit()
    return SubscribeResponse(message="Subscribed successfully", email=req.email)


@app.get("/api/macro")
def get_macro_trends(db: Session = Depends(get_db)):
    trends = db.query(MacroTrend).order_by(MacroTrend.change_1d.desc()).all()
    return [t.to_dict() for t in trends]


@app.get("/api/macro/{sector}/stocks")
def get_sector_stocks(
    sector: str,
    db: Session = Depends(get_db),
):
    """Get signal stocks that belong to a given sector (matching sector ETF name)."""
    etf_name_to_sector = {v: v for v in SECTOR_ETFS.values()}
    sector_name = etf_name_to_sector.get(sector, sector)
    stocks = (
        db.query(StockSignal)
        .filter(StockSignal.sector == sector_name)
        .order_by(desc(StockSignal.rating))
        .all()
    )
    return [s.to_summary() for s in stocks]


@app.get("/api/search")
def search_tickers(q: str = Query("", min_length=1, max_length=10)):
    """Search for tickers using Yahoo Finance."""
    import yfinance as yf
    q = q.upper().strip()
    results = []
    try:
        data = yf.download(q, period="5d", interval="1d", progress=False, session=yf_session)
        if not data.empty:
            name = q
            try:
                info = yf.Ticker(q, session=yf_session).info
                if info:
                    name = info.get("shortName", info.get("longName", q))
            except Exception:
                pass
            results.append({
                "ticker": q,
                "name": name,
                "exchange": "",
            })
    except Exception:
        pass
    return results


class WatchlistAddRequest(BaseModel):
    ticker: str


@app.get("/api/watchlist")
def list_watchlist(db: Session = Depends(get_db)):
    import math
    import yfinance as yf
    import pandas as pd

    items = db.query(WatchlistItem).order_by(WatchlistItem.created_at.desc()).all()
    if not items:
        return []

    tickers = [item.ticker for item in items]
    live_data: dict[str, dict] = {}
    fundamentals_data: dict[str, dict] = {}

    try:
        data = yf.download(
            tickers,
            period="8mo",
            interval="1d",
            group_by="ticker",
            threads=True,
            progress=False,
            session=yf_session,
        )
        if not data.empty:
            for ticker in tickers:
                try:
                    if len(tickers) == 1:
                        close = data["Close"].dropna()
                    else:
                        close = data[(ticker, "Close")].dropna()

                    if len(close) < 2:
                        continue

                    sma30 = close.rolling(window=30).mean()
                    current_price = float(close.iloc[-1])
                    current_sma = float(sma30.iloc[-1]) if not pd.isna(sma30.iloc[-1]) else None

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

                    live_data[ticker] = {
                        "current_price": round(current_price, 2),
                        "sma30": round(current_sma, 2) if current_sma else None,
                        "above_sma": current_price > current_sma if current_sma else None,
                        "weekly_sma30": w_sma30,
                        "above_weekly_sma": w_above,
                        "change_pct": round(
                            (current_price - float(close.iloc[-2])) / float(close.iloc[-2]) * 100, 2
                        ) if len(close) >= 2 else 0,
                    }
                except Exception:
                    continue
    except Exception:
        logger.warning("Failed to download watchlist live data")

    def _safe(v, default=0):
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return default
        return v

    for ticker in tickers:
        try:
            info = yf.Ticker(ticker, session=yf_session).info
            if not info:
                continue
            fundamentals_data[ticker] = {
                "market_cap": _safe(info.get("marketCap")),
                "revenue": _safe(info.get("totalRevenue")),
                "pe_ratio": info.get("trailingPE"),
                "revenue_growth": info.get("revenueGrowth"),
                "operating_margin": info.get("operatingMargins"),
                "operating_cashflow": _safe(info.get("operatingCashflow")),
                "free_cashflow": _safe(info.get("freeCashflow")),
                "ps_ratio": info.get("priceToSalesTrailing12Months"),
                "pb_ratio": info.get("priceToBook"),
                "avg_volume": _safe(info.get("averageVolume")),
            }
        except Exception:
            continue

    result = []
    for item in items:
        entry = item.to_dict()
        entry["live"] = live_data.get(item.ticker)

        signal = (
            db.query(StockSignal)
            .filter(StockSignal.ticker == item.ticker)
            .order_by(desc(StockSignal.crossover_date))
            .first()
        )
        entry["signal"] = signal.to_summary() if signal else None

        fund = fundamentals_data.get(item.ticker)
        live = live_data.get(item.ticker)
        if fund and live and live.get("sma30"):
            rating_result = rate_signal(
                price=live["current_price"],
                sma30=live["sma30"],
                market_cap=fund["market_cap"],
                revenue=fund["revenue"],
                pe_ratio=fund["pe_ratio"],
                avg_volume=fund["avg_volume"],
                revenue_growth=fund["revenue_growth"],
                operating_margin=fund["operating_margin"],
                free_cashflow=fund["free_cashflow"],
                ps_ratio=fund["ps_ratio"],
            )
            entry["fundamentals"] = fund
            entry["rating"] = rating_result.stars
            entry["rating_reasons"] = rating_result.to_list()
        else:
            entry["fundamentals"] = fund
            entry["rating"] = None
            entry["rating_reasons"] = []

        result.append(entry)
    return result


@app.post("/api/watchlist")
def add_to_watchlist(req: WatchlistAddRequest, db: Session = Depends(get_db)):
    ticker = req.ticker.upper().strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker is required")

    existing = db.query(WatchlistItem).filter(WatchlistItem.ticker == ticker).first()
    if existing:
        entry = existing.to_dict()
        signal = (
            db.query(StockSignal)
            .filter(StockSignal.ticker == existing.ticker)
            .order_by(desc(StockSignal.crossover_date))
            .first()
        )
        entry["signal"] = signal.to_summary() if signal else None
        return entry

    company_name = ticker
    try:
        import yfinance as yf
        data = yf.download(ticker, period="5d", interval="1d", progress=False, session=yf_session)
        if data.empty:
            raise HTTPException(status_code=400, detail=f"Ticker '{ticker}' not found")
        try:
            info = yf.Ticker(ticker, session=yf_session).info
            if info:
                company_name = info.get("shortName", info.get("longName", ticker))
        except Exception:
            pass
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail=f"Could not verify ticker '{ticker}'")

    item = WatchlistItem(ticker=ticker, company_name=company_name)
    db.add(item)
    db.commit()
    db.refresh(item)
    entry = item.to_dict()
    entry["signal"] = None
    return entry


@app.delete("/api/watchlist/{ticker}")
def remove_from_watchlist(ticker: str, db: Session = Depends(get_db)):
    item = db.query(WatchlistItem).filter(WatchlistItem.ticker == ticker.upper()).first()
    if not item:
        raise HTTPException(status_code=404, detail="Ticker not in watchlist")
    db.delete(item)
    db.commit()
    return {"message": f"{ticker.upper()} removed from watchlist"}


@app.get("/api/watchlist/tickers")
def get_watchlist_tickers(db: Session = Depends(get_db)):
    """Return just the list of watchlist ticker strings (for quick lookups)."""
    items = db.query(WatchlistItem.ticker).all()
    return [t[0] for t in items]


@app.post("/api/scan")
def trigger_scan():
    """Scanning runs locally via cron. Use local_scan.py instead."""
    return {
        "message": "Scanning is handled locally via cron job. "
        "Run 'python local_scan.py' from the backend directory."
    }
