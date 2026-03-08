import { useState, useEffect, useRef } from 'react';
import { useAddToWatchlist } from '../hooks/useStocks';
import { searchTickers, type TickerSearchResult } from '../lib/api';

export default function WatchlistSearch() {
  const [input, setInput] = useState('');
  const [suggestions, setSuggestions] = useState<TickerSearchResult[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [searching, setSearching] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'ok' | 'err'; msg: string } | null>(null);
  const addMutation = useAddToWatchlist();
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!feedback) return;
    const t = setTimeout(() => setFeedback(null), 2500);
    return () => clearTimeout(t);
  }, [feedback]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const doSearch = (q: string) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (q.length < 1) {
      setSuggestions([]);
      setShowDropdown(false);
      return;
    }
    debounceRef.current = setTimeout(async () => {
      setSearching(true);
      try {
        const results = await searchTickers(q);
        setSuggestions(results);
        setShowDropdown(results.length > 0);
      } catch {
        setSuggestions([]);
      } finally {
        setSearching(false);
      }
    }, 300);
  };

  const handleInputChange = (val: string) => {
    setInput(val);
    doSearch(val.trim());
  };

  const addTicker = (ticker: string) => {
    if (!ticker) return;
    setShowDropdown(false);
    addMutation.mutate(ticker, {
      onSuccess: () => {
        setInput('');
        setSuggestions([]);
        setFeedback({ type: 'ok', msg: `✓ ${ticker}` });
      },
      onError: (err: Error) => {
        const msg = err.message.includes('400') ? `'${ticker}' not found` : 'failed to add';
        setFeedback({ type: 'err', msg });
      },
    });
  };

  const handleSubmit = () => {
    const ticker = input.trim().toUpperCase();
    if (ticker) addTicker(ticker);
  };

  return (
    <div className="relative" ref={wrapperRef}>
      <div className="flex items-center gap-1">
        <div className="relative">
          <input
            type="text"
            value={input}
            onChange={(e) => handleInputChange(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
            onFocus={() => suggestions.length > 0 && setShowDropdown(true)}
            placeholder="add ticker..."
            className="bg-[#0d120d] border border-[#1a2a1a] px-2 py-1 text-[11px] text-[#c0d0c0] placeholder-[#2a3a2a] w-36 focus:outline-none focus:border-[#4ade80]/40"
          />
          {searching && (
            <div className="absolute right-2 top-1/2 -translate-y-1/2">
              <div className="w-3 h-3 border border-[#3a4a3a] border-t-[#4ade80] rounded-full animate-spin" />
            </div>
          )}
        </div>
        <button
          onClick={handleSubmit}
          disabled={addMutation.isPending || !input.trim()}
          className="border border-[#1a2a1a] text-[#4a5a4a] text-[11px] px-2 py-1 hover:text-[#4ade80] hover:border-[#4ade80]/30 disabled:opacity-30 transition-colors"
        >
          {addMutation.isPending ? '...' : '+'}
        </button>
        {feedback && (
          <span className={`text-[10px] animate-fade-in ${feedback.type === 'ok' ? 'text-[#4ade80]' : 'text-[#f87171]'}`}>
            {feedback.msg}
          </span>
        )}
      </div>

      {showDropdown && suggestions.length > 0 && (
        <div className="absolute top-full left-0 mt-1 w-64 bg-[#0d120d] border border-[#1a2a1a] z-50 max-h-48 overflow-y-auto">
          {suggestions.map((s) => (
            <button
              key={s.ticker}
              onClick={() => addTicker(s.ticker)}
              className="w-full text-left px-3 py-2 text-[11px] hover:bg-[#4ade80]/5 transition-colors flex items-center justify-between"
            >
              <span>
                <span className="text-[#c0d0c0] font-medium">{s.ticker}</span>
                {s.name !== s.ticker && (
                  <span className="text-[#3a4a3a] ml-2 truncate">{s.name}</span>
                )}
              </span>
              {s.exchange && <span className="text-[9px] text-[#2a3a2a]">{s.exchange}</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
