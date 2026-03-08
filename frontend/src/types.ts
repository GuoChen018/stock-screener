export interface PricePoint {
  time: number;
  value: number;
  open?: number;
  high?: number;
  low?: number;
  close?: number;
  sma: number | null;
}

export interface RatingReason {
  criterion: string;
  passed: boolean;
  detail: string;
}

export interface StockSummary {
  id: number;
  ticker: string;
  company_name: string;
  sector: string;
  market_cap: number;
  revenue: number;
  pe_ratio: number | null;
  revenue_growth: number | null;
  operating_margin: number | null;
  operating_cashflow: number;
  free_cashflow: number;
  ps_ratio: number | null;
  pb_ratio: number | null;
  price_at_crossover: number;
  sma30_at_crossover: number;
  weekly_sma30: number | null;
  above_weekly_sma: boolean | null;
  crossover_date: string;
  current_price: number;
  price_change_pct: number;
  signal_type: 'bullish' | 'bearish';
  rating: number;
  rating_reasons: RatingReason[];
  price_history: PricePoint[];
}

export interface StockDetail extends StockSummary {
  industry: string;
  avg_volume: number;
  news: NewsItem[];
  created_at: string;
  updated_at: string;
}

export interface NewsItem {
  title: string;
  url: string;
  publisher: string;
  published: string;
}

export interface StocksResponse {
  stocks: StockSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface StatsResponse {
  total_signals: number;
  sectors: Record<string, number>;
}

export interface WatchlistLive {
  current_price: number;
  sma30: number | null;
  above_sma: boolean | null;
  weekly_sma30: number | null;
  above_weekly_sma: boolean | null;
  change_pct: number;
}

export interface WatchlistFundamentals {
  market_cap: number;
  revenue: number;
  pe_ratio: number | null;
  revenue_growth: number | null;
  operating_margin: number | null;
  operating_cashflow: number;
  free_cashflow: number;
  ps_ratio: number | null;
  pb_ratio: number | null;
  avg_volume: number;
}

export interface WatchlistItem {
  id: number;
  ticker: string;
  company_name: string;
  created_at: string;
  live: WatchlistLive | null;
  signal: StockSummary | null;
  fundamentals: WatchlistFundamentals | null;
  rating: number | null;
  rating_reasons: RatingReason[];
}

export interface MacroTrend {
  id: number;
  name: string;
  ticker: string;
  current_value: number;
  change_1d: number;
  change_1w: number;
  change_1m: number;
  trend: 'up' | 'down' | 'flat';
  updated_at: string;
}
