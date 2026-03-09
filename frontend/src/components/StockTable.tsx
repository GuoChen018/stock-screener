import { useState } from 'react';
import type { StockSummary } from '../types';
import MiniChart from './MiniChart';
import RatingPanel from './RatingPanel';
import { useWatchlistTickers, useAddToWatchlist, useRemoveFromWatchlist } from '../hooks/useStocks';

interface StockTableProps {
  stocks: StockSummary[];
  onSelect: (ticker: string) => void;
  selectedTicker: string | null;
  sortBy: string;
  sortDir: string;
  onSort: (column: string) => void;
  signalType?: string;
}

function StarRating({ rating, onClick }: { rating: number; onClick: (e: React.MouseEvent) => void }) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-0.5 hover:opacity-80 transition-opacity group"
      title="Click for details"
    >
      {[1, 2, 3, 4, 5].map((i) => (
        <svg
          key={i}
          width="10"
          height="10"
          viewBox="0 0 24 24"
          fill={i <= rating ? '#4ade80' : 'none'}
          stroke={i <= rating ? '#4ade80' : '#1a2a1a'}
          strokeWidth="2"
          strokeLinejoin="round"
          className="transition-transform group-hover:scale-110"
        >
          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
        </svg>
      ))}
    </button>
  );
}

function SortIcon({ active, dir }: { active: boolean; dir: string }) {
  if (!active) {
    return (
      <svg width="10" height="10" viewBox="0 0 12 12" className="opacity-0 group-hover/th:opacity-40 transition-opacity ml-1 inline-block">
        <path d="M6 2l3 4H3z" fill="currentColor" />
        <path d="M6 10l3-4H3z" fill="currentColor" />
      </svg>
    );
  }
  return (
    <svg width="10" height="10" viewBox="0 0 12 12" className="text-[#4ade80] ml-1 inline-block">
      {dir === 'asc'
        ? <path d="M6 2l3 4H3z" fill="currentColor" />
        : <path d="M6 10l3-4H3z" fill="currentColor" />
      }
    </svg>
  );
}

function formatCap(cap: number): string {
  if (cap >= 1e12) return `${(cap / 1e12).toFixed(1)}T`;
  if (cap >= 1e9) return `${(cap / 1e9).toFixed(1)}B`;
  if (cap >= 1e6) return `${(cap / 1e6).toFixed(0)}M`;
  return cap.toLocaleString();
}

function formatDate(iso: string): string {
  return new Date(iso + 'T00:00:00').toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
}

interface ColumnDef {
  key: string;
  label: string;
  align: 'left' | 'center' | 'right';
  sortable: boolean;
  className?: string;
}

function BookmarkIcon({ filled, onClick }: { filled: boolean; onClick: (e: React.MouseEvent) => void }) {
  return (
    <button onClick={onClick} className="hover:opacity-80 transition-opacity" title={filled ? 'Remove from watchlist' : 'Add to watchlist'}>
      <svg width="14" height="14" viewBox="0 0 24 24" fill={filled ? '#4ade80' : 'none'} stroke={filled ? '#4ade80' : '#2a3a2a'} strokeWidth="2">
        <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
      </svg>
    </button>
  );
}

const COLUMNS: ColumnDef[] = [
  { key: 'bookmark', label: '', align: 'center', sortable: false, className: 'w-8' },
  { key: 'ticker', label: 'TICKER', align: 'left', sortable: true },
  { key: 'rating', label: 'RATING', align: 'center', sortable: true },
  { key: 'sector', label: 'SECTOR', align: 'left', sortable: true },
  { key: 'market_cap', label: 'MKT_CAP', align: 'right', sortable: true },
  { key: 'current_price', label: 'PRICE', align: 'right', sortable: true },
  { key: 'weekly_sma30', label: 'SMA30', align: 'right', sortable: true },
  { key: 'above_weekly_sma', label: 'VS SMA', align: 'center', sortable: true },
  { key: 'price_change_pct', label: '%CHG', align: 'right', sortable: true },
  { key: 'chart', label: 'CHART', align: 'center', sortable: false, className: 'w-32' },
  { key: 'crossover_date', label: 'DATE', align: 'right', sortable: true },
];

export default function StockTable({ stocks, onSelect, selectedTicker, sortBy, sortDir, onSort, signalType }: StockTableProps) {
  const [ratingPanel, setRatingPanel] = useState<StockSummary | null>(null);
  const { data: watchlistTickers } = useWatchlistTickers();
  const addToWl = useAddToWatchlist();
  const removeFromWl = useRemoveFromWatchlist();

  const wlSet = new Set(watchlistTickers || []);

  const toggleWatchlist = (e: React.MouseEvent, ticker: string) => {
    e.stopPropagation();
    if (wlSet.has(ticker)) {
      removeFromWl.mutate(ticker);
    } else {
      addToWl.mutate(ticker);
    }
  };

  if (stocks.length === 0) {
    let title = 'no signals found';
    let hint = 'run a scan to detect sma 30 crossovers';

    if (signalType === 'bearish') {
      title = 'no below sma signals';
      hint = 'stocks that dropped below sma 30 will appear after running a scan';
    } else if (signalType === 'bullish') {
      title = 'no above sma signals';
      hint = 'run a scan to detect stocks above sma 30';
    }

    return (
      <div className="text-center py-16 text-[#3a4a3a]">
        <p className="text-xs">{title}</p>
        <p className="text-[10px] mt-1">{hint}</p>
      </div>
    );
  }

  return (
    <>
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-[#1a2a1a]">
            {COLUMNS.map((col) => (
              <th
                key={col.key}
                className={`py-2 px-3 text-[11px] font-medium text-[#3a4a3a] group/th ${
                  col.className || ''
                } ${col.sortable ? 'cursor-pointer select-none hover:text-[#4ade80] transition-colors' : ''} ${
                  col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left'
                }`}
                onClick={col.sortable ? () => onSort(col.key) : undefined}
              >
                {col.label}
                {col.sortable && <SortIcon active={sortBy === col.key} dir={sortDir} />}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {stocks.map((stock) => (
            <tr
              key={stock.id}
              onClick={() => onSelect(stock.ticker)}
              className={`border-b border-[#1a2a1a]/50 cursor-pointer transition-colors ${
                selectedTicker === stock.ticker
                  ? 'bg-[#4ade80]/5'
                  : 'hover:bg-[#0a150a]'
              }`}
            >
              <td className="py-2 px-2 text-center">
                <BookmarkIcon
                  filled={wlSet.has(stock.ticker)}
                  onClick={(e) => toggleWatchlist(e, stock.ticker)}
                />
              </td>
              <td className="py-2 px-3">
                <div className="font-semibold text-sm text-[#c0d0c0]">{stock.ticker}</div>
                <div className="text-[10px] text-[#3a4a3a] truncate max-w-[160px]">{stock.company_name}</div>
              </td>
              <td className="py-2 px-3 text-center">
                <StarRating
                  rating={stock.rating}
                  onClick={(e) => {
                    e.stopPropagation();
                    setRatingPanel(stock);
                  }}
                />
              </td>
              <td className="py-2 px-3">
                <span className="text-xs text-[#4a5a4a]">
                  {stock.sector || '--'}
                </span>
              </td>
              <td className="py-2 px-3 text-right text-[#6a7a6a]">
                {formatCap(stock.market_cap)}
              </td>
              <td className="py-2 px-3 text-right text-[#c0d0c0] font-medium">
                ${stock.current_price.toFixed(2)}
              </td>
              <td className="py-2 px-3 text-right text-[#4a5a4a] text-xs">
                {stock.weekly_sma30 != null ? `$${stock.weekly_sma30.toFixed(2)}` : '—'}
              </td>
              <td className="py-2 px-3 text-center text-xs">
                {stock.above_weekly_sma != null ? (
                  <span className={`px-1.5 py-0.5 rounded ${
                    stock.above_weekly_sma
                      ? 'bg-[#4ade80]/10 text-[#4ade80]'
                      : 'bg-[#f87171]/10 text-[#f87171]'
                  }`}>
                    {stock.above_weekly_sma ? 'above' : 'below'}
                  </span>
                ) : (
                  <span className="text-[#3a4a3a]">—</span>
                )}
              </td>
              <td className="py-2 px-3 text-right font-medium">
                <span className={stock.price_change_pct >= 0 ? 'text-[#4ade80]' : 'text-[#f87171]'}>
                  {stock.price_change_pct >= 0 ? '+' : ''}{stock.price_change_pct.toFixed(2)}%
                </span>
              </td>
              <td className="py-1 px-3">
                <MiniChart data={stock.price_history} sma30={stock.sma30_at_crossover} />
              </td>
              <td className="py-2 px-3 text-right text-[#3a4a3a] text-xs">
                {formatDate(stock.crossover_date)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>

    {ratingPanel && (
      <RatingPanel
        ticker={ratingPanel.ticker}
        rating={ratingPanel.rating}
        reasons={ratingPanel.rating_reasons}
        onClose={() => setRatingPanel(null)}
      />
    )}
    </>
  );
}
