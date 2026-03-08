"""
Rules-based stock signal rating system.

Scores each SMA 30 crossover signal on five criteria, awarding 0 or 1 star each
for a total rating of 0-5. Every criterion produces an explanation string so the
user can see exactly why a stock got its rating.
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class RatingResult:
    stars: int
    reasons: list[dict] = field(default_factory=list)

    def to_list(self) -> list[dict]:
        return self.reasons


def rate_signal(
    price: float,
    sma30: float,
    market_cap: int,
    revenue: int,
    pe_ratio: float | None,
    avg_volume: int,
    revenue_growth: float | None = None,
    operating_margin: float | None = None,
    free_cashflow: int = 0,
    ps_ratio: float | None = None,
) -> RatingResult:
    stars = 0
    reasons: list[dict] = []

    # --- Star 1: Crossover Strength ---
    if sma30 > 0:
        pct_above = ((price - sma30) / sma30) * 100
    else:
        pct_above = 0.0

    if pct_above >= 1.0:
        stars += 1
        reasons.append({
            "criterion": "Crossover Strength",
            "passed": True,
            "detail": f"Price is {pct_above:.1f}% above SMA 30 — a decisive crossover with conviction.",
        })
    else:
        reasons.append({
            "criterion": "Crossover Strength",
            "passed": False,
            "detail": f"Price is only {pct_above:.1f}% above SMA 30 — barely crossing, could easily reverse.",
        })

    # --- Star 2: Volume Confirmation ---
    if avg_volume >= 1_000_000:
        stars += 1
        reasons.append({
            "criterion": "Volume Confirmation",
            "passed": True,
            "detail": f"Average daily volume of {avg_volume / 1e6:.1f}M shares — highly liquid, institutional interest.",
        })
    elif avg_volume >= 500_000:
        stars += 1
        reasons.append({
            "criterion": "Volume Confirmation",
            "passed": True,
            "detail": f"Average daily volume of {avg_volume / 1e3:.0f}K shares — adequate liquidity.",
        })
    else:
        reasons.append({
            "criterion": "Volume Confirmation",
            "passed": False,
            "detail": f"Average daily volume of {avg_volume / 1e3:.0f}K shares — low liquidity, harder to enter/exit.",
        })

    # --- Star 3: Revenue Quality ---
    has_strong_revenue = revenue > 1_000_000_000
    has_growth = revenue_growth is not None and revenue_growth > 0.10
    detail_parts = []

    if has_strong_revenue:
        detail_parts.append(f"revenue ${revenue / 1e9:.1f}B")
    elif revenue > 0:
        detail_parts.append(f"revenue ${revenue / 1e6:.0f}M")
    else:
        detail_parts.append("no revenue data")

    if revenue_growth is not None:
        detail_parts.append(f"growth {revenue_growth * 100:.1f}%")
    else:
        detail_parts.append("no growth data")

    if has_strong_revenue and has_growth:
        stars += 1
        reasons.append({
            "criterion": "Revenue Quality",
            "passed": True,
            "detail": f"Strong revenue profile: {', '.join(detail_parts)}.",
        })
    else:
        reasons.append({
            "criterion": "Revenue Quality",
            "passed": False,
            "detail": f"Revenue needs improvement: {', '.join(detail_parts)}.",
        })

    # --- Star 4: Profitability ---
    has_positive_margin = operating_margin is not None and operating_margin > 0
    has_positive_fcf = free_cashflow > 0
    profit_parts = []

    if operating_margin is not None:
        profit_parts.append(f"operating margin {operating_margin * 100:.1f}%")
    else:
        profit_parts.append("no margin data")

    if free_cashflow != 0:
        if free_cashflow > 0:
            profit_parts.append(f"FCF ${free_cashflow / 1e6:.0f}M")
        else:
            profit_parts.append(f"FCF -${abs(free_cashflow) / 1e6:.0f}M (burning cash)")
    else:
        profit_parts.append("no FCF data")

    if has_positive_margin and has_positive_fcf:
        stars += 1
        reasons.append({
            "criterion": "Profitability",
            "passed": True,
            "detail": f"Profitable business: {', '.join(profit_parts)}.",
        })
    else:
        reasons.append({
            "criterion": "Profitability",
            "passed": False,
            "detail": f"Profitability concerns: {', '.join(profit_parts)}.",
        })

    # --- Star 5: Valuation Sanity ---
    reasonable_pe = pe_ratio is not None and 0 < pe_ratio <= 60
    reasonable_ps = ps_ratio is not None and 0 < ps_ratio < 15
    val_parts = []

    if pe_ratio is not None:
        if pe_ratio < 0:
            val_parts.append(f"P/E {pe_ratio:.1f} (unprofitable)")
        else:
            val_parts.append(f"P/E {pe_ratio:.1f}")
    else:
        val_parts.append("no P/E data")

    if ps_ratio is not None:
        val_parts.append(f"P/S {ps_ratio:.1f}")
    else:
        val_parts.append("no P/S data")

    if reasonable_pe or reasonable_ps:
        stars += 1
        reasons.append({
            "criterion": "Valuation Sanity",
            "passed": True,
            "detail": f"Reasonably valued: {', '.join(val_parts)}.",
        })
    else:
        reasons.append({
            "criterion": "Valuation Sanity",
            "passed": False,
            "detail": f"Valuation concern: {', '.join(val_parts)}.",
        })

    return RatingResult(stars=stars, reasons=reasons)
