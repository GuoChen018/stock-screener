import WatchlistSearch from './WatchlistSearch';

interface FilterBarProps {
  signalType: string;
  watchlistOnly: boolean;
  onSignalTypeChange: (type: string) => void;
  onWatchlistToggle: (on: boolean) => void;
}

const SIGNAL_TABS = [
  { value: '', label: 'ALL' },
  { value: 'bullish', label: 'ABOVE SMA' },
  { value: 'bearish', label: 'BELOW SMA' },
];

export default function FilterBar({
  signalType,
  watchlistOnly,
  onSignalTypeChange,
  onWatchlistToggle,
}: FilterBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="flex border border-[#1a2a1a] overflow-hidden">
        {SIGNAL_TABS.map((tab) => {
          const isActive = !watchlistOnly && signalType === tab.value;
          return (
            <button
              key={tab.value}
              onClick={() => onSignalTypeChange(tab.value)}
              className={`px-3 py-1.5 text-[11px] transition-colors border-r border-[#1a2a1a] last:border-r-0 ${
                isActive
                  ? tab.value === 'bearish'
                    ? 'bg-[#f87171]/10 text-[#f87171]'
                    : 'bg-[#4ade80]/10 text-[#4ade80]'
                  : 'text-[#4a5a4a] hover:text-[#8a9a8a]'
              }`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      <button
        onClick={() => onWatchlistToggle(!watchlistOnly)}
        className={`px-3 py-1.5 text-[11px] border transition-colors ${
          watchlistOnly
            ? 'border-[#4ade80]/40 bg-[#4ade80]/10 text-[#4ade80]'
            : 'border-[#1a2a1a] text-[#4a5a4a] hover:text-[#8a9a8a]'
        }`}
      >
        ★ watchlist
      </button>

      <WatchlistSearch />
    </div>
  );
}
