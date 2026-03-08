import { useState, useCallback, useRef } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useStocks, useStats } from './hooks/useStocks';
import StockTable from './components/StockTable';
import StockDetail from './components/StockDetail';
import WatchlistTable from './components/WatchlistTable';
import FilterBar from './components/FilterBar';
import SubscribeForm from './components/SubscribeForm';
import { triggerScan } from './lib/api';
import type { StockFilters } from './lib/api';

const queryClient = new QueryClient();

function formatNum(n: number): string {
  return n.toLocaleString();
}

function Dashboard() {
  const [filters, setFilters] = useState<StockFilters>({
    sort_by: 'rating',
    sort_dir: 'desc',
    limit: 50,
  });
  const [watchlistActive, setWatchlistActive] = useState(false);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [closing, setClosing] = useState(false);
  const [scanning, setScanning] = useState(false);
  const closingRef = useRef(false);

  const closePanel = useCallback(() => {
    if (closingRef.current) return;
    closingRef.current = true;
    setClosing(true);
    setTimeout(() => {
      setSelectedTicker(null);
      setClosing(false);
      closingRef.current = false;
    }, 200);
  }, []);

  const { data, isLoading, refetch } = useStocks(filters);
  const { data: stats } = useStats();

  const handleScan = useCallback(async () => {
    setScanning(true);
    try {
      await triggerScan();
      queryClient.invalidateQueries();
      await refetch();
    } finally {
      setScanning(false);
    }
  }, [refetch]);

  return (
    <div className="min-h-screen bg-[#0a0f0a]">
      <header className="border-b border-[#1a2a1a] bg-[#0a0f0a]/90 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 py-3">
          <div className="flex flex-col sm:flex-row sm:items-center gap-3">
            <div className="flex-1 min-w-0">
              <h1 className="text-base font-bold text-[#4ade80] tracking-tight">
                sma30-screener
              </h1>
              <p className="text-xs text-[#3a4a3a] mt-0.5">
                sma 30 crossover signals
                {stats && (
                  <span className="text-[#2a3a2a]"> // {formatNum(stats.total_signals)} signal{stats.total_signals !== 1 ? 's' : ''}</span>
                )}
              </p>
            </div>
            <SubscribeForm />
          </div>
        </div>
      </header>

      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 py-4">
        <div className="mb-4">
          <FilterBar
            sector={filters.sector || ''}
            signalType={filters.signal_type || ''}
            watchlistOnly={watchlistActive}
            onSectorChange={(sector) => setFilters((f) => ({ ...f, sector: sector || undefined, offset: 0 }))}
            onSignalTypeChange={(type) => { setWatchlistActive(false); setFilters((f) => ({ ...f, signal_type: type || undefined, offset: 0 })); }}
            onWatchlistToggle={(on) => setWatchlistActive(on)}
            onScan={handleScan}
            scanning={scanning}
          />
        </div>

        <div className="border border-[#1a2a1a] rounded overflow-hidden bg-[#0d120d]">
          {watchlistActive ? (
            <WatchlistTable
              onSelect={setSelectedTicker}
              selectedTicker={selectedTicker}
            />
          ) : isLoading ? (
            <div className="p-8 text-center text-[#3a4a3a]">
              <div className="inline-block w-4 h-4 border border-[#3a4a3a] border-t-[#4ade80] rounded-full animate-spin mb-3" />
              <p className="text-xs">loading...</p>
            </div>
          ) : (
            <>
              <StockTable
                stocks={data?.stocks || []}
                onSelect={setSelectedTicker}
                selectedTicker={selectedTicker}
                sortBy={filters.sort_by || 'rating'}
                sortDir={filters.sort_dir || 'desc'}
                signalType={filters.signal_type}
                onSort={(column) => {
                  setFilters((f) => ({
                    ...f,
                    sort_by: column,
                    sort_dir: f.sort_by === column && f.sort_dir === 'desc' ? 'asc' : 'desc',
                    offset: 0,
                  }));
                }}
              />
              {data && data.total > data.limit && (
                <div className="flex items-center justify-between px-4 py-2 border-t border-[#1a2a1a]">
                  <span className="text-[10px] text-[#3a4a3a]">
                    {data.offset + 1}-{Math.min(data.offset + data.limit, data.total)} of {data.total}
                  </span>
                  <div className="flex gap-2">
                    <button
                      disabled={data.offset === 0}
                      onClick={() => setFilters((f) => ({ ...f, offset: Math.max(0, (f.offset || 0) - (f.limit || 50)) }))}
                      className="text-[10px] px-2 py-1 border border-[#1a2a1a] text-[#4a5a4a] hover:text-[#4ade80] hover:border-[#4ade80]/30 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    >
                      prev
                    </button>
                    <button
                      disabled={data.offset + data.limit >= data.total}
                      onClick={() => setFilters((f) => ({ ...f, offset: (f.offset || 0) + (f.limit || 50) }))}
                      className="text-[10px] px-2 py-1 border border-[#1a2a1a] text-[#4a5a4a] hover:text-[#4ade80] hover:border-[#4ade80]/30 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    >
                      next
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </main>

      {selectedTicker && (
        <>
          <div
            className={`fixed inset-0 bg-black/50 z-40 ${closing ? 'animate-fade-out' : 'animate-fade-in'}`}
            onClick={closePanel}
          />
          <div className={`fixed top-0 right-0 h-screen w-full sm:w-[640px] z-50 ${closing ? 'animate-slide-out' : 'animate-slide-in'}`}>
            <StockDetail
              ticker={selectedTicker}
              onClose={closePanel}
            />
          </div>
        </>
      )}
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Dashboard />
    </QueryClientProvider>
  );
}
