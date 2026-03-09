import { useState } from 'react';
import { useWatchlist, useRemoveFromWatchlist } from '../hooks/useStocks';
import type { WatchlistItem } from '../types';
import RatingPanel from './RatingPanel';

interface WatchlistTableProps {
  onSelect: (ticker: string) => void;
  selectedTicker: string | null;
}

function formatCap(cap: number): string {
  if (cap >= 1e12) return `${(cap / 1e12).toFixed(1)}T`;
  if (cap >= 1e9) return `${(cap / 1e9).toFixed(1)}B`;
  if (cap >= 1e6) return `${(cap / 1e6).toFixed(0)}M`;
  return cap.toLocaleString();
}

function WatchlistStarRating({ rating, onClick }: { rating: number | null; onClick: (e: React.MouseEvent) => void }) {
  if (rating == null) return <span className="text-[10px] text-[#2a3a2a]">--</span>;
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

function formatMargin(val: number | null | undefined): string {
  if (val == null) return '--';
  return `${(val * 100).toFixed(1)}%`;
}

function formatPE(val: number | null | undefined): string {
  if (val == null) return '--';
  return val.toFixed(1);
}

function WatchlistRow({ item, onSelect, isSelected, onRemove, onRatingClick }: {
  item: WatchlistItem;
  onSelect: (ticker: string) => void;
  isSelected: boolean;
  onRemove: (ticker: string) => void;
  onRatingClick: (item: WatchlistItem) => void;
}) {
  const live = item.live;
  const sig = item.signal;
  const fund = item.fundamentals;

  return (
    <tr
      onClick={() => onSelect(item.ticker)}
      className={`border-b border-[#1a2a1a]/50 transition-colors cursor-pointer ${
        isSelected ? 'bg-[#4ade80]/5' : 'hover:bg-[#0a150a]'
      }`}
    >
      <td className="py-2.5 px-3">
        <button
          onClick={(e) => { e.stopPropagation(); onRemove(item.ticker); }}
          className="text-[#3a4a3a] hover:text-[#f87171] transition-colors"
          title="Remove from watchlist"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="#4ade80" stroke="#4ade80" strokeWidth="2">
            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
          </svg>
        </button>
      </td>
      <td className="py-2.5 px-3">
        <div className="font-semibold text-sm text-[#c0d0c0]">{item.ticker}</div>
        <div className="text-[10px] text-[#3a4a3a] truncate max-w-[200px]">{item.company_name}</div>
      </td>
      <td className="py-2.5 px-3 text-center">
        <WatchlistStarRating
          rating={item.rating}
          onClick={(e) => { e.stopPropagation(); onRatingClick(item); }}
        />
      </td>
      <td className="py-2.5 px-3 text-right text-xs">
        {live ? (
          <span className="text-[#c0d0c0] font-medium">${live.current_price.toFixed(2)}</span>
        ) : (
          <span className="text-[#2a3a2a]">--</span>
        )}
      </td>
      <td className="py-2.5 px-3 text-center">
        {live?.above_weekly_sma != null ? (
          <span className={`text-[10px] px-1.5 py-0.5 rounded ${
            live.above_weekly_sma
              ? 'bg-[#4ade80]/10 text-[#4ade80]'
              : 'bg-[#f87171]/10 text-[#f87171]'
          }`}>
            {live.above_weekly_sma ? 'above' : 'below'}
          </span>
        ) : (
          <span className="text-[10px] text-[#2a3a2a]">--</span>
        )}
      </td>
      <td className="py-2.5 px-3 text-right text-xs">
        {live ? (
          <span className={live.change_pct >= 0 ? 'text-[#4ade80]' : 'text-[#f87171]'}>
            {live.change_pct >= 0 ? '+' : ''}{live.change_pct.toFixed(2)}%
          </span>
        ) : (
          <span className="text-[#2a3a2a]">--</span>
        )}
      </td>
      <td className="py-2.5 px-3 text-right text-xs text-[#4a5a4a]">
        {fund ? formatCap(fund.market_cap) : sig ? formatCap(sig.market_cap) : '--'}
      </td>
      <td className="py-2.5 px-3 text-right text-xs text-[#4a5a4a]">
        {formatMargin(fund?.operating_margin)}
      </td>
      <td className="py-2.5 px-3 text-right text-xs text-[#4a5a4a]">
        {formatPE(fund?.pe_ratio)}
      </td>
    </tr>
  );
}

export default function WatchlistTable({ onSelect, selectedTicker }: WatchlistTableProps) {
  const { data: items, isLoading } = useWatchlist();
  const removeMutation = useRemoveFromWatchlist();
  const [ratingPanel, setRatingPanel] = useState<WatchlistItem | null>(null);

  if (isLoading) {
    return (
      <div className="p-8 text-center text-[#3a4a3a]">
        <div className="inline-block w-4 h-4 border border-[#3a4a3a] border-t-[#4ade80] rounded-full animate-spin mb-3" />
        <p className="text-xs">loading watchlist...</p>
      </div>
    );
  }

  if (!items || items.length === 0) {
    return (
      <div className="text-center py-16 text-[#3a4a3a]">
        <p className="text-xs">your watchlist is empty</p>
        <p className="text-[10px] mt-1">use the search box above to add tickers, or bookmark stocks from the main table</p>
      </div>
    );
  }

  return (
    <>
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-[#1a2a1a]">
            <th className="py-2 px-3 text-[11px] font-medium text-[#3a4a3a] w-8" />
            <th className="py-2 px-3 text-[11px] font-medium text-[#3a4a3a] text-left">TICKER</th>
            <th className="py-2 px-3 text-[11px] font-medium text-[#3a4a3a] text-center">RATING</th>
            <th className="py-2 px-3 text-[11px] font-medium text-[#3a4a3a] text-right">PRICE</th>
            <th className="py-2 px-3 text-[11px] font-medium text-[#3a4a3a] text-center">VS SMA</th>
            <th className="py-2 px-3 text-[11px] font-medium text-[#3a4a3a] text-right">%CHG</th>
            <th className="py-2 px-3 text-[11px] font-medium text-[#3a4a3a] text-right">MKT_CAP</th>
            <th className="py-2 px-3 text-[11px] font-medium text-[#3a4a3a] text-right">MARGIN</th>
            <th className="py-2 px-3 text-[11px] font-medium text-[#3a4a3a] text-right">P/E</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <WatchlistRow
              key={item.id}
              item={item}
              onSelect={onSelect}
              isSelected={selectedTicker === item.ticker}
              onRemove={(ticker) => removeMutation.mutate(ticker)}
              onRatingClick={(item) => setRatingPanel(item)}
            />
          ))}
        </tbody>
      </table>
    </div>

    {ratingPanel && ratingPanel.rating != null && (
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
