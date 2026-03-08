from __future__ import annotations

import logging
from dataclasses import dataclass, field

import resend

from app.config import RESEND_API_KEY

logger = logging.getLogger(__name__)

FONT = "'Helvetica Neue', Helvetica, Arial, sans-serif"
GREEN = "#22c55e"
RED = "#ef4444"
TEXT = "#1a1a1a"
TEXT_DIM = "#666666"
TEXT_MUTED = "#999999"
BORDER = "#e5e5e5"
TH = f"text-align:left;padding:6px 10px;color:{TEXT_MUTED};font-size:11px;text-transform:uppercase;letter-spacing:0.04em;border-bottom:2px solid {BORDER}"
TD = f"padding:6px 10px;font-size:13px;border-bottom:1px solid {BORDER}"


@dataclass
class RecapStock:
    ticker: str
    company_name: str
    price: float
    sma30: float
    rating: int | None = None
    market_cap: int = 0
    operating_margin: float | None = None
    pe_ratio: float | None = None
    weekly_sma30: float | None = None
    above_weekly_sma: bool | None = None
    status: str = ""


@dataclass
class DailyRecap:
    watchlist_stocks: list[RecapStock] = field(default_factory=list)
    top_above: list[RecapStock] = field(default_factory=list)
    top_below: list[RecapStock] = field(default_factory=list)


def send_daily_recap(subscribers: list[str], recap: DailyRecap):
    if not subscribers:
        return
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not configured, skipping email")
        return

    wl_sorted = sorted(recap.watchlist_stocks, key=lambda s: -(s.rating or 0))
    top_above = sorted(recap.top_above, key=lambda s: -(s.rating or 0))[:10]
    top_below = sorted(recap.top_below, key=lambda s: -(s.rating or 0))[:10]

    if not (wl_sorted or top_above or top_below):
        logger.info("Nothing to report in daily recap, skipping email")
        return

    resend.api_key = RESEND_API_KEY

    sections = ""

    if wl_sorted:
        sections += _section("Your Watchlist", f"{len(wl_sorted)} tracked stock(s)", wl_sorted, show_status=True)
    else:
        sections += _empty_section("Your Watchlist", "No stocks in your watchlist yet.")

    if top_above:
        sections += _section("Crossed Above SMA 30", f"Top {len(top_above)} by rating", top_above)
    else:
        sections += _empty_section("Crossed Above SMA 30", "No new bullish crossovers today.")

    if top_below:
        sections += _section("Crossed Below SMA 30", f"Top {len(top_below)} by rating", top_below)
    else:
        sections += _empty_section("Crossed Below SMA 30", "No new bearish crossovers today.")

    count = len(wl_sorted) + len(top_above) + len(top_below)

    html = f"""<div style="font-family:{FONT};color:{TEXT}">
    <h1 style="font-size:22px;font-weight:700;margin:0 0 4px">SMA 30 Daily Recap</h1>
    <p style="font-size:13px;color:{TEXT_DIM};margin:0 0 24px">{count} stock(s) in today's recap</p>
    {sections}
    <p style="font-size:10px;color:{TEXT_MUTED};margin:24px 0 0">Not financial advice. Ratings based on crossover strength, volume, revenue quality, profitability, and valuation.</p>
</div>"""

    for email in subscribers:
        try:
            resend.Emails.send({
                "from": "Stock Screener <onboarding@resend.dev>",
                "to": [email],
                "subject": f"SMA 30 Daily Recap — {count} stock(s)",
                "html": html,
            })
            logger.info("Daily recap sent to %s", email)
        except Exception:
            logger.exception("Failed to send email to %s", email)


def _section(title: str, subtitle: str, stocks: list[RecapStock], show_status: bool = False) -> str:
    return f"""
    <div style="margin:0 0 28px">
        <h2 style="font-size:17px;font-weight:700;color:{TEXT};margin:0 0 2px">{title}</h2>
        <p style="font-size:12px;color:{TEXT_DIM};margin:0 0 12px">{subtitle}</p>
        {_build_table(stocks, show_status)}
    </div>"""


def _empty_section(title: str, message: str) -> str:
    return f"""
    <div style="margin:0 0 28px">
        <h2 style="font-size:17px;font-weight:700;color:{TEXT};margin:0 0 2px">{title}</h2>
        <p style="font-size:12px;color:{TEXT_MUTED};font-style:italic;margin:8px 0 0">{message}</p>
    </div>"""


def _build_table(stocks: list[RecapStock], show_status: bool = False) -> str:
    rows = ""
    for s in stocks:
        stars_filled = s.rating or 0
        stars = (
            f'<span style="color:{GREEN}">' + "★" * stars_filled + '</span>'
            + f'<span style="color:#ddd">' + "☆" * (5 - stars_filled) + '</span>'
        )

        status_cell = ""
        if show_status:
            is_above = "above" in s.status
            sc = GREEN if is_above else RED
            status_cell = f'<td style="{TD};color:{sc};font-weight:600;font-size:12px">{s.status}</td>'

        if s.above_weekly_sma is not None:
            wc = GREEN if s.above_weekly_sma else RED
            wl = "above" if s.above_weekly_sma else "below"
            wsma_cell = f'<td style="{TD};text-align:center;color:{wc};font-size:12px">{wl}</td>'
        else:
            wsma_cell = f'<td style="{TD};text-align:center;color:{TEXT_MUTED}">—</td>'

        rows += f"""
        <tr>
            <td style="{TD};font-weight:700">{s.ticker}</td>
            {status_cell}
            <td style="{TD};text-align:right;font-weight:600">${s.price:.2f}</td>
            <td style="{TD};text-align:right;color:{TEXT_DIM}">${s.sma30:.2f}</td>
            {wsma_cell}
            <td style="{TD};text-align:right;color:{TEXT_DIM}">{_format_market_cap(s.market_cap)}</td>
            <td style="{TD};text-align:center;letter-spacing:1px">{stars}</td>
        </tr>"""

    status_header = ""
    if show_status:
        status_header = f'<th style="{TH}">Status</th>'

    return f"""
    <table style="width:100%;border-collapse:collapse;table-layout:fixed">
        <thead>
            <tr>
                <th style="{TH}">Ticker</th>
                {status_header}
                <th style="{TH};text-align:right">Price</th>
                <th style="{TH};text-align:right">SMA30</th>
                <th style="{TH};text-align:center">W-SMA</th>
                <th style="{TH};text-align:right">Mkt Cap</th>
                <th style="{TH};text-align:center">Rating</th>
            </tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>"""


def _format_market_cap(cap: int) -> str:
    if cap >= 1_000_000_000_000:
        return f"${cap / 1_000_000_000_000:.1f}T"
    if cap >= 1_000_000_000:
        return f"${cap / 1_000_000_000:.1f}B"
    if cap >= 1_000_000:
        return f"${cap / 1_000_000:.0f}M"
    return f"${cap:,}"
