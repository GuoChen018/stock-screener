import { useMacroTrends } from '../hooks/useStocks';
import type { MacroTrend } from '../types';

interface MacroBarProps {
  onSectorClick: (sector: string) => void;
}

function TrendPill({ trend, onClick }: { trend: MacroTrend; onClick: () => void }) {
  const color =
    trend.trend === 'up'
      ? 'text-[#4ade80] border-[#4ade80]/20 hover:border-[#4ade80]/40 hover:bg-[#4ade80]/5'
      : trend.trend === 'down'
        ? 'text-[#f87171] border-[#f87171]/20 hover:border-[#f87171]/40 hover:bg-[#f87171]/5'
        : 'text-[#6a7a6a] border-[#1a2a1a] hover:border-[#3a4a3a]';

  const arrow = trend.trend === 'up' ? '↑' : trend.trend === 'down' ? '↓' : '→';

  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-2.5 py-1 border rounded text-[10px] transition-colors whitespace-nowrap ${color}`}
    >
      <span className="font-medium">{trend.ticker}</span>
      <span className="opacity-60">{trend.name}</span>
      <span>
        {arrow} {trend.change_1d >= 0 ? '+' : ''}{trend.change_1d.toFixed(1)}%
      </span>
    </button>
  );
}

export default function MacroBar({ onSectorClick }: MacroBarProps) {
  const { data: trends } = useMacroTrends();

  if (!trends || trends.length === 0) return null;

  const indices = trends.filter((t) =>
    ['SPY', 'QQQ', 'DIA'].includes(t.ticker)
  );
  const sectors = trends.filter(
    (t) => !['SPY', 'QQQ', 'DIA'].includes(t.ticker)
  );

  return (
    <div className="border border-[#1a2a1a] rounded bg-[#0d120d] p-3 mb-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-[10px] text-[#3a4a3a] uppercase tracking-wider">// indices</span>
        <div className="flex flex-wrap gap-1.5">
          {indices.map((t) => (
            <TrendPill key={t.ticker} trend={t} onClick={() => {}} />
          ))}
        </div>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-[10px] text-[#3a4a3a] uppercase tracking-wider">// sectors</span>
        <div className="flex flex-wrap gap-1.5">
          {sectors.map((t) => (
            <TrendPill
              key={t.ticker}
              trend={t}
              onClick={() => onSectorClick(t.name)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
