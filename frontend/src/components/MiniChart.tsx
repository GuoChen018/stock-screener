import { AreaChart, Area, ReferenceLine, ResponsiveContainer, YAxis } from 'recharts';
import type { PricePoint } from '../types';

interface MiniChartProps {
  data: PricePoint[];
  sma30: number;
  height?: number;
}

export default function MiniChart({ data, sma30, height = 36 }: MiniChartProps) {
  if (!data || data.length === 0) {
    return <div className="h-9 w-full bg-[#1a2a1a]/30 rounded-sm" />;
  }

  const values = data.map((d) => d.value);
  const min = Math.min(...values) * 0.998;
  const max = Math.max(...values) * 1.002;

  return (
    <div style={{ height, width: '100%', minWidth: 100 }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 2, right: 0, bottom: 2, left: 0 }}>
          <defs>
            <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#4ade80" stopOpacity={0.2} />
              <stop offset="100%" stopColor="#4ade80" stopOpacity={0} />
            </linearGradient>
          </defs>
          <YAxis domain={[min, max]} hide />
          <ReferenceLine y={sma30} stroke="#f59e0b" strokeDasharray="2 2" strokeWidth={0.5} />
          <Area
            type="monotone"
            dataKey="value"
            stroke="#4ade80"
            fill="url(#priceGrad)"
            strokeWidth={1}
            dot={false}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
