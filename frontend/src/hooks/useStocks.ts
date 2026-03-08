import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchStocks,
  fetchStock,
  fetchStats,
  fetchSectors,
  fetchWatchlist,
  fetchWatchlistTickers,
  addToWatchlist,
  removeFromWatchlist,
  fetchMacroTrends,
  type StockFilters,
} from '../lib/api';

export function useStocks(filters: StockFilters = {}) {
  return useQuery({
    queryKey: ['stocks', filters],
    queryFn: () => fetchStocks(filters),
    staleTime: 60_000,
  });
}

export function useStock(ticker: string | null) {
  return useQuery({
    queryKey: ['stock', ticker],
    queryFn: () => fetchStock(ticker!),
    enabled: !!ticker,
    staleTime: 60_000,
  });
}

export function useStats() {
  return useQuery({
    queryKey: ['stats'],
    queryFn: fetchStats,
    staleTime: 60_000,
  });
}

export function useSectors() {
  return useQuery({
    queryKey: ['sectors'],
    queryFn: fetchSectors,
    staleTime: 300_000,
  });
}

export function useWatchlistTickers() {
  return useQuery({
    queryKey: ['watchlist-tickers'],
    queryFn: fetchWatchlistTickers,
    staleTime: 30_000,
  });
}

export function useWatchlist() {
  return useQuery({
    queryKey: ['watchlist'],
    queryFn: fetchWatchlist,
    staleTime: 30_000,
  });
}

export function useAddToWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: addToWatchlist,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['watchlist-tickers'] });
      qc.invalidateQueries({ queryKey: ['watchlist'] });
      qc.invalidateQueries({ queryKey: ['stocks'] });
    },
  });
}

export function useRemoveFromWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: removeFromWatchlist,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['watchlist-tickers'] });
      qc.invalidateQueries({ queryKey: ['watchlist'] });
      qc.invalidateQueries({ queryKey: ['stocks'] });
    },
  });
}

export function useMacroTrends() {
  return useQuery({
    queryKey: ['macro-trends'],
    queryFn: fetchMacroTrends,
    staleTime: 60_000,
  });
}
