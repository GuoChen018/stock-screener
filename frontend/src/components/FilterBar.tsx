import { useSectors } from '../hooks/useStocks';
import WatchlistSearch from './WatchlistSearch';

interface FilterBarProps {
  sector: string;
  signalType: string;
  watchlistOnly: boolean;
  onSectorChange: (sector: string) => void;
  onSignalTypeChange: (type: string) => void;
  onWatchlistToggle: (on: boolean) => void;
  onScan: () => void;
  scanning: boolean;
}

const SIGNAL_TABS = [
  { value: '', label: 'ALL' },
  { value: 'bullish', label: 'ABOVE SMA' },
  { value: 'bearish', label: 'BELOW SMA' },
];

export default function FilterBar({
  sector,
  signalType,
  watchlistOnly,
  onSectorChange,
  onSignalTypeChange,
  onWatchlistToggle,
  onScan,
  scanning,
}: FilterBarProps) {
  const { data: sectors } = useSectors();

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

      <select
        value={sector}
        onChange={(e) => onSectorChange(e.target.value)}
        className="bg-[#0d120d] border border-[#1a2a1a] px-2 py-1.5 text-[11px] text-[#6a7a6a] focus:outline-none focus:border-[#4ade80]/40"
      >
        <option value="">all_sectors</option>
        {sectors?.map((s) => (
          <option key={s} value={s}>{s.toLowerCase()}</option>
        ))}
      </select>

      <WatchlistSearch />

      <button
        onClick={onScan}
        disabled={scanning}
        className="ml-auto border border-[#4ade80]/40 text-[#4ade80] text-[11px] px-3 py-1.5 hover:bg-[#4ade80]/10 disabled:border-[#1a2a1a] disabled:text-[#3a4a3a] transition-colors"
      >
        {scanning ? 'scanning...' : '> run_scan'}
      </button>
    </div>
  );
}
