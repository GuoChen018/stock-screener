import json
import math
from datetime import datetime, date

from sqlalchemy import Boolean, String, Float, Integer, Date, DateTime, Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _json_safe(v):
    """Replace NaN/Inf floats with None for JSON serialization."""
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


class StockSignal(Base):
    __tablename__ = "stock_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(10), index=True)
    company_name: Mapped[str] = mapped_column(String(200), default="")
    sector: Mapped[str] = mapped_column(String(100), default="")
    industry: Mapped[str] = mapped_column(String(200), default="")
    market_cap: Mapped[int] = mapped_column(BigInteger, default=0)
    revenue: Mapped[int] = mapped_column(BigInteger, default=0)
    pe_ratio: Mapped[float] = mapped_column(Float, nullable=True)
    revenue_growth: Mapped[float] = mapped_column(Float, nullable=True)
    operating_margin: Mapped[float] = mapped_column(Float, nullable=True)
    operating_cashflow: Mapped[int] = mapped_column(BigInteger, default=0)
    free_cashflow: Mapped[int] = mapped_column(BigInteger, default=0)
    ps_ratio: Mapped[float] = mapped_column(Float, nullable=True)
    pb_ratio: Mapped[float] = mapped_column(Float, nullable=True)
    avg_volume: Mapped[int] = mapped_column(BigInteger, default=0)
    price_at_crossover: Mapped[float] = mapped_column(Float, default=0.0)
    sma30_at_crossover: Mapped[float] = mapped_column(Float, default=0.0)
    weekly_sma30: Mapped[float] = mapped_column(Float, nullable=True)
    above_weekly_sma: Mapped[bool] = mapped_column(Boolean, nullable=True)
    crossover_date: Mapped[date] = mapped_column(Date, index=True)
    current_price: Mapped[float] = mapped_column(Float, default=0.0)
    price_change_pct: Mapped[float] = mapped_column(Float, default=0.0)
    signal_type: Mapped[str] = mapped_column(String(10), default="bullish")
    rating: Mapped[int] = mapped_column(Integer, default=0)
    rating_reasons_json: Mapped[str] = mapped_column(Text, default="[]")
    news_json: Mapped[str] = mapped_column(Text, default="[]")
    price_history_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    @property
    def rating_reasons(self) -> list[dict]:
        return json.loads(self.rating_reasons_json) if self.rating_reasons_json else []

    @rating_reasons.setter
    def rating_reasons(self, value: list[dict]):
        self.rating_reasons_json = json.dumps(value)

    @property
    def news(self) -> list[dict]:
        return json.loads(self.news_json) if self.news_json else []

    @news.setter
    def news(self, value: list[dict]):
        self.news_json = json.dumps(value)

    @property
    def price_history(self) -> list[dict]:
        return json.loads(self.price_history_json) if self.price_history_json else []

    @price_history.setter
    def price_history(self, value: list[dict]):
        self.price_history_json = json.dumps(value)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ticker": self.ticker,
            "company_name": self.company_name,
            "sector": self.sector,
            "industry": self.industry,
            "market_cap": self.market_cap,
            "revenue": self.revenue,
            "pe_ratio": _json_safe(self.pe_ratio),
            "revenue_growth": _json_safe(self.revenue_growth),
            "operating_margin": _json_safe(self.operating_margin),
            "operating_cashflow": self.operating_cashflow,
            "free_cashflow": self.free_cashflow,
            "ps_ratio": _json_safe(self.ps_ratio),
            "pb_ratio": _json_safe(self.pb_ratio),
            "avg_volume": self.avg_volume,
            "price_at_crossover": self.price_at_crossover,
            "sma30_at_crossover": self.sma30_at_crossover,
            "weekly_sma30": _json_safe(self.weekly_sma30),
            "above_weekly_sma": self.above_weekly_sma,
            "crossover_date": self.crossover_date.isoformat() if self.crossover_date else None,
            "current_price": self.current_price,
            "price_change_pct": _json_safe(self.price_change_pct),
            "signal_type": self.signal_type,
            "rating": self.rating,
            "rating_reasons": self.rating_reasons,
            "news": self.news,
            "price_history": self.price_history,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_summary(self) -> dict:
        return {
            "id": self.id,
            "ticker": self.ticker,
            "company_name": self.company_name,
            "sector": self.sector,
            "market_cap": self.market_cap,
            "revenue": self.revenue,
            "pe_ratio": _json_safe(self.pe_ratio),
            "revenue_growth": _json_safe(self.revenue_growth),
            "operating_margin": _json_safe(self.operating_margin),
            "operating_cashflow": self.operating_cashflow,
            "free_cashflow": self.free_cashflow,
            "ps_ratio": _json_safe(self.ps_ratio),
            "pb_ratio": _json_safe(self.pb_ratio),
            "price_at_crossover": self.price_at_crossover,
            "sma30_at_crossover": self.sma30_at_crossover,
            "weekly_sma30": _json_safe(self.weekly_sma30),
            "above_weekly_sma": self.above_weekly_sma,
            "crossover_date": self.crossover_date.isoformat() if self.crossover_date else None,
            "current_price": self.current_price,
            "price_change_pct": _json_safe(self.price_change_pct),
            "signal_type": self.signal_type,
            "rating": self.rating,
            "rating_reasons": self.rating_reasons,
            "price_history": self.price_history,
        }


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    company_name: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ticker": self.ticker,
            "company_name": self.company_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class MacroTrend(Base):
    __tablename__ = "macro_trends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    ticker: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    current_value: Mapped[float] = mapped_column(Float, default=0.0)
    change_1d: Mapped[float] = mapped_column(Float, default=0.0)
    change_1w: Mapped[float] = mapped_column(Float, default=0.0)
    change_1m: Mapped[float] = mapped_column(Float, default=0.0)
    trend: Mapped[str] = mapped_column(String(10), default="flat")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "ticker": self.ticker,
            "current_value": self.current_value,
            "change_1d": self.change_1d,
            "change_1w": self.change_1w,
            "change_1m": self.change_1m,
            "trend": self.trend,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Subscriber(Base):
    __tablename__ = "subscribers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
