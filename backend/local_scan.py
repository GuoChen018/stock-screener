#!/usr/bin/env python3
"""
Local scan script -- runs the full SMA 30 crossover scan, builds the
watchlist recap, and sends the daily email.

Connects to Neon PostgreSQL via DATABASE_URL in .env so results are
visible on the deployed frontend/API.

Usage:
    python local_scan.py          # full scan + email
    python local_scan.py --email  # watchlist email only (no market scan)
"""

import asyncio
import logging
import sys

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("local_scan")

from app.database import SessionLocal, init_db
from app.emailer import send_daily_recap, DailyRecap, RecapStock
from app.models import Subscriber
from app.scanner import run_scan, backfill_ohlc
from app.macro import scan_macro_trends
from app.scheduler import _build_watchlist_recap


def main():
    email_only = "--email" in sys.argv

    init_db()
    db = SessionLocal()

    try:
        top_above = []
        top_below = []

        if not email_only:
            logger.info("Starting full market scan...")
            signals = asyncio.run(run_scan(db))
            logger.info("Scan found %d qualifying stocks", len(signals))

            for s in signals:
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

            backfill_ohlc(db)
            scan_macro_trends(db)
        else:
            logger.info("Email-only mode, skipping market scan")

        logger.info("Building watchlist recap...")
        watchlist_stocks = _build_watchlist_recap(db)
        logger.info("Watchlist: %d stocks", len(watchlist_stocks))

        recap = DailyRecap(
            watchlist_stocks=watchlist_stocks,
            top_above=top_above,
            top_below=top_below,
        )

        subscribers = [
            s.email for s in db.query(Subscriber).filter(Subscriber.active).all()
        ]

        if subscribers:
            logger.info("Sending email to %d subscriber(s)...", len(subscribers))
            send_daily_recap(subscribers, recap)
        else:
            logger.warning("No subscribers, skipping email")

        total = len(watchlist_stocks) + len(top_above) + len(top_below)
        logger.info(
            "Done! watchlist=%d, above=%d, below=%d, total=%d",
            len(watchlist_stocks), len(top_above), len(top_below), total,
        )
    except Exception:
        logger.exception("Scan failed")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
