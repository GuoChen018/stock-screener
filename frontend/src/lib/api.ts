import type { StocksResponse, StockDetail, StatsResponse, WatchlistItem, MacroTrend } from '../types';

const BASE = `${import.meta.env.VITE_API_URL || ''}/api`;

async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, init);
  if (!res.ok) throw new Error(`${res.status}: ${res.statusText}`);
  return res.json();
}

export interface StockFilters {
  sector?: string;
  signal_type?: string;
  min_market_cap?: number;
  max_market_cap?: number;
  sort_by?: string;
  sort_dir?: string;
  limit?: number;
  offset?: number;
}

export function fetchStocks(filters: StockFilters = {}): Promise<StocksResponse> {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== '') params.set(k, String(v));
  });
  const qs = params.toString();
  return fetchJSON(`/stocks${qs ? `?${qs}` : ''}`);
}

export function fetchStock(ticker: string): Promise<StockDetail> {
  return fetchJSON(`/stocks/${ticker}`);
}

export function fetchStats(): Promise<StatsResponse> {
  return fetchJSON('/stats');
}

export function fetchSectors(): Promise<string[]> {
  return fetchJSON('/sectors');
}

export function subscribe(email: string) {
  return fetchJSON<{ message: string; email: string }>('/subscribe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
}

export function triggerScan() {
  return fetchJSON<{ message: string; new_signals: number; total_signals: number }>(
    '/scan',
    { method: 'POST' },
  );
}

export function fetchWatchlist(): Promise<WatchlistItem[]> {
  return fetchJSON('/watchlist');
}

export function fetchWatchlistTickers(): Promise<string[]> {
  return fetchJSON('/watchlist/tickers');
}

export function addToWatchlist(ticker: string): Promise<WatchlistItem> {
  return fetchJSON('/watchlist', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ticker }),
  });
}

export function removeFromWatchlist(ticker: string): Promise<{ message: string }> {
  return fetchJSON(`/watchlist/${ticker}`, { method: 'DELETE' });
}

export function fetchMacroTrends(): Promise<MacroTrend[]> {
  return fetchJSON('/macro');
}

export interface TickerSearchResult {
  ticker: string;
  name: string;
  exchange: string;
}

export function searchTickers(q: string): Promise<TickerSearchResult[]> {
  return fetchJSON(`/search?q=${encodeURIComponent(q)}`);
}
