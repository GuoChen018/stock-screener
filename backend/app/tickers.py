import io
import logging

import httpx
import pandas as pd

logger = logging.getLogger(__name__)

NASDAQ_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqtraded.txt"


async def fetch_all_us_tickers() -> list[str]:
    """Fetch all actively-traded US equity tickers from NASDAQ trader."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(NASDAQ_URL)
            resp.raise_for_status()

        df = pd.read_csv(io.StringIO(resp.text), sep="|")
        df = df[df["Test Issue"] == "N"]
        df = df[df["ETF"] == "N"]
        df = df[df["Financial Status"] == "N"]

        tickers = df["Symbol"].dropna().unique().tolist()
        tickers = [
            t.strip()
            for t in tickers
            if isinstance(t, str)
            and t.strip()
            and not any(c in t for c in ["$", ".", "-"])
        ]
        logger.info("Fetched %d US equity tickers", len(tickers))
        return sorted(tickers)
    except Exception:
        logger.exception("Failed to fetch tickers from NASDAQ, using fallback")
        return await _fallback_tickers()


async def _fallback_tickers() -> list[str]:
    """Fallback: fetch S&P 500 tickers from Wikipedia."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            )
            resp.raise_for_status()

        tables = pd.read_html(io.StringIO(resp.text))
        df = tables[0]
        tickers = df["Symbol"].str.replace(".", "-", regex=False).tolist()
        logger.info("Fallback: fetched %d S&P 500 tickers", len(tickers))
        return sorted(tickers)
    except Exception:
        logger.exception("Fallback ticker fetch also failed")
        return []
