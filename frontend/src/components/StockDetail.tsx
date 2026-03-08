import { Liveline } from 'liveline';
import type { CandlePoint } from 'liveline';
import { useStock } from '../hooks/useStocks';
import type { NewsItem } from '../types';

interface StockDetailProps {
  ticker: string;
  onClose: () => void;
}

function formatCap(cap: number): string {
  if (cap >= 1e12) return `${(cap / 1e12).toFixed(1)}T`;
  if (cap >= 1e9) return `${(cap / 1e9).toFixed(1)}B`;
  if (cap >= 1e6) return `${(cap / 1e6).toFixed(0)}M`;
  return cap.toLocaleString();
}

function formatRevenue(rev: number): string {
  if (!rev) return '--';
  if (rev >= 1e9) return `$${(rev / 1e9).toFixed(1)}B`;
  if (rev >= 1e6) return `$${(rev / 1e6).toFixed(0)}M`;
  return `$${rev.toLocaleString()}`;
}

function formatCashflow(val: number): string {
  if (!val) return '--';
  const prefix = val < 0 ? '-$' : '$';
  const abs = Math.abs(val);
  if (abs >= 1e9) return `${prefix}${(abs / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `${prefix}${(abs / 1e6).toFixed(0)}M`;
  return `${prefix}${abs.toLocaleString()}`;
}

function formatPct(val: number | null): string {
  if (val == null) return '--';
  return `${(val * 100).toFixed(1)}%`;
}

function formatRatio(val: number | null): string {
  if (val == null) return '--';
  return val.toFixed(1);
}

function NewsCard({ item }: { item: NewsItem }) {
  return (
    <a
      href={item.url}
      target="_blank"
      rel="noopener noreferrer"
      className="block px-3 py-2 border border-[#1a2a1a] hover:border-[#4ade80]/30 hover:bg-[#0a150a] transition-colors"
    >
      <p className="text-xs text-[#8a9a8a] leading-snug line-clamp-2">{item.title}</p>
      <p className="text-[11px] text-[#3a4a3a] mt-1">{item.publisher}</p>
    </a>
  );
}

export default function StockDetail({ ticker, onClose }: StockDetailProps) {
  const { data: stock, isLoading, error } = useStock(ticker);

  if (isLoading) {
    return (
      <div className="h-full bg-[#0d120d] border-l border-[#1a2a1a] p-5 animate-pulse">
        <div className="h-4 bg-[#1a2a1a] rounded w-24 mb-4" />
        <div className="h-40 bg-[#1a2a1a] rounded mb-4" />
        <div className="h-3 bg-[#1a2a1a] rounded w-full mb-2" />
        <div className="h-3 bg-[#1a2a1a] rounded w-3/4" />
      </div>
    );
  }

  if (error || !stock) {
    return (
      <div className="h-full bg-[#0d120d] border-l border-[#1a2a1a] p-5">
        <p className="text-red-400 text-xs">error: failed to load data</p>
        <button onClick={onClose} className="text-[10px] text-[#3a4a3a] mt-2 underline">close</button>
      </div>
    );
  }

  const history = stock.price_history || [];

  const chartData = history.map((p) => ({
    time: p.time,
    value: p.value,
  }));

  const hasOHLC = history.length > 0 && history[0].open != null;
  const candleData: CandlePoint[] = hasOHLC
    ? history.map((p) => ({
        time: p.time,
        open: p.open!,
        high: p.high!,
        low: p.low!,
        close: p.close ?? p.value,
      }))
    : [];

  const latestValue = chartData.length > 0 ? chartData[chartData.length - 1].value : 0;
  const timeRange = chartData.length > 1
    ? chartData[chartData.length - 1].time - chartData[0].time
    : 86400;

  return (
    <div className="h-full bg-[#0d120d] border-l border-[#1a2a1a] flex flex-col overflow-y-auto">
      <div className="flex items-center justify-between px-5 py-4 border-b border-[#1a2a1a]">
        <div className="flex items-baseline gap-3">
          <h2 className="text-sm font-bold text-[#4ade80]">{stock.ticker}</h2>
          <span className="text-xl font-bold text-[#c0d0c0]">
            ${stock.current_price.toFixed(2)}
          </span>
          <span
            className={`text-xs ${
              stock.price_change_pct >= 0 ? 'text-[#4ade80]' : 'text-[#f87171]'
            }`}
          >
            {stock.price_change_pct >= 0 ? '+' : ''}{stock.price_change_pct.toFixed(2)}%
          </span>
        </div>
        <button
          onClick={onClose}
          className="text-[#3a4a3a] hover:text-[#4ade80] transition-colors text-xs"
          aria-label="Close"
        >
          [x]
        </button>
      </div>

      <div className="px-1 py-1 text-[11px] text-[#3a4a3a] border-b border-[#1a2a1a]">
        <span className="px-4">{stock.company_name} // {stock.sector || 'n/a'} // {stock.industry || 'n/a'}</span>
      </div>

      <div className="px-2 pt-3 pb-6 border-b border-[#1a2a1a]">
        <div style={{ height: 300 }}>
          {chartData.length > 0 ? (
            <Liveline
              data={chartData}
              value={latestValue}
              window={timeRange}
              theme="dark"
              color="#4ade80"
              mode={hasOHLC ? 'candle' : 'line'}
              candles={hasOHLC ? candleData : undefined}
              candleWidth={86400}
              referenceLine={{ value: stock.sma30_at_crossover, label: `D-SMA30 · $${stock.sma30_at_crossover.toFixed(2)}${stock.weekly_sma30 != null ? `  |  W-SMA30 · $${stock.weekly_sma30.toFixed(2)}` : ''}` }}
              showValue
              valueMomentumColor
              momentum={hasOHLC ? false : true}
              scrub
              grid
              badge={false}
              exaggerate={!hasOHLC}
              fill={!hasOHLC}
              formatValue={(v: number) => `$${v.toFixed(2)}`}
              formatTime={(t: number) => {
                const d = new Date(t * 1000);
                return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
              }}
              padding={{ top: 12, right: 100, bottom: 48, left: 12 }}
            />
          ) : (
            <div className="h-full flex items-center justify-center text-[#3a4a3a] text-xs">
              no chart data
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-4 border-b border-[#1a2a1a]">
        {[
          { k: 'mkt_cap', v: formatCap(stock.market_cap) },
          { k: 'revenue', v: formatRevenue(stock.revenue) },
          { k: 'rev_growth', v: formatPct(stock.revenue_growth) },
          { k: 'op_margin', v: formatPct(stock.operating_margin) },
          { k: 'ocf', v: formatCashflow(stock.operating_cashflow) },
          { k: 'fcf', v: formatCashflow(stock.free_cashflow) },
          { k: 'p/e', v: formatRatio(stock.pe_ratio) },
          { k: 'p/s', v: formatRatio(stock.ps_ratio) },
          { k: 'p/b', v: formatRatio(stock.pb_ratio) },
          { k: 'avg_vol', v: stock.avg_volume ? `${(stock.avg_volume / 1e6).toFixed(1)}M` : '--' },
          { k: 'sma_30', v: `$${stock.sma30_at_crossover.toFixed(2)}` },
          { k: 'w_sma30', v: stock.weekly_sma30 != null ? `$${stock.weekly_sma30.toFixed(2)}` : '--' },
          { k: 'cross_dt', v: new Date(stock.crossover_date + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) },
          { k: 'sector', v: stock.sector || '--' },
          { k: 'industry', v: stock.industry || '--' },
        ].map((item) => (
          <div key={item.k} className="px-3 py-2 border-r border-b border-[#1a2a1a] last:border-r-0">
            <div className="text-[10px] text-[#3a4a3a] uppercase">{item.k}</div>
            <div className="text-xs text-[#8a9a8a] mt-0.5 truncate">{item.v}</div>
          </div>
        ))}
      </div>

      {stock.news && stock.news.length > 0 && (
        <div className="p-4 flex-1">
          <h3 className="text-[10px] text-[#3a4a3a] uppercase tracking-wider mb-2">// recent news</h3>
          <div className="space-y-1">
            {stock.news.map((item, i) => (
              <NewsCard key={i} item={item} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
