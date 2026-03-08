import logging
from datetime import datetime

import yfinance as yf
from sqlalchemy.orm import Session

from app.models import MacroTrend
from app.yf_session import session as yf_session

logger = logging.getLogger(__name__)

SECTOR_ETFS = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLE": "Energy",
    "XLV": "Healthcare",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLI": "Industrials",
    "XLB": "Materials",
    "XLRE": "Real Estate",
    "XLC": "Communication Services",
    "XLU": "Utilities",
}

INDEX_ETFS = {
    "SPY": "S&P 500",
    "QQQ": "Nasdaq 100",
    "DIA": "Dow Jones",
}

ALL_ETFS = {**SECTOR_ETFS, **INDEX_ETFS}


def scan_macro_trends(db: Session):
    """Download sector/index ETF data and compute trend metrics."""
    tickers = list(ALL_ETFS.keys())
    logger.info("Scanning %d macro ETFs", len(tickers))

    try:
        data = yf.download(
            tickers,
            period="3mo",
            interval="1d",
            group_by="ticker",
            threads=True,
            progress=False,
            session=yf_session,
        )
    except Exception:
        logger.exception("Failed to download macro ETF data")
        return

    if data.empty:
        logger.warning("Macro ETF download returned empty data")
        return

    for ticker, name in ALL_ETFS.items():
        try:
            if len(tickers) == 1:
                close = data["Close"].dropna()
            else:
                close = data[(ticker, "Close")].dropna()

            if len(close) < 5:
                continue

            current = float(close.iloc[-1])
            prev_1d = float(close.iloc[-2]) if len(close) >= 2 else current
            prev_1w = float(close.iloc[-5]) if len(close) >= 5 else current
            prev_1m = float(close.iloc[-22]) if len(close) >= 22 else close.iloc[0]

            change_1d = round((current - prev_1d) / prev_1d * 100, 2) if prev_1d else 0
            change_1w = round((current - prev_1w) / prev_1w * 100, 2) if prev_1w else 0
            change_1m = round((current - float(prev_1m)) / float(prev_1m) * 100, 2) if prev_1m else 0

            if change_1w > 1:
                trend = "up"
            elif change_1w < -1:
                trend = "down"
            else:
                trend = "flat"

            existing = db.query(MacroTrend).filter(MacroTrend.ticker == ticker).first()
            if existing:
                existing.name = name
                existing.current_value = current
                existing.change_1d = change_1d
                existing.change_1w = change_1w
                existing.change_1m = change_1m
                existing.trend = trend
                existing.updated_at = datetime.utcnow()
            else:
                mt = MacroTrend(
                    name=name,
                    ticker=ticker,
                    current_value=current,
                    change_1d=change_1d,
                    change_1w=change_1w,
                    change_1m=change_1m,
                    trend=trend,
                )
                db.add(mt)

        except Exception:
            logger.warning("Failed to process macro ETF %s", ticker)
            continue

    db.commit()
    logger.info("Macro trend scan complete")
