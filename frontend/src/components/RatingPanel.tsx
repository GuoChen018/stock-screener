import type { RatingReason } from '../types';

interface RatingPanelProps {
  ticker: string;
  rating: number;
  reasons: RatingReason[];
  onClose: () => void;
}

function Star({ filled }: { filled: boolean }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill={filled ? '#4ade80' : 'none'}
      stroke={filled ? '#4ade80' : '#1a2a1a'}
      strokeWidth="2"
      strokeLinejoin="round"
    >
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
    </svg>
  );
}

export default function RatingPanel({ ticker, rating, reasons, onClose }: RatingPanelProps) {
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/70 animate-fade-in" />
      <div
        className="relative bg-[#0d120d] border border-[#1a2a1a] max-w-md w-full shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#1a2a1a]">
          <div>
            <h3 className="text-xs font-bold text-[#4ade80]">{ticker} // rating</h3>
            <div className="flex items-center gap-1 mt-1">
              {[1, 2, 3, 4, 5].map((i) => (
                <Star key={i} filled={i <= rating} />
              ))}
              <span className="text-[10px] text-[#3a4a3a] ml-2">{rating}/5</span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-[#3a4a3a] hover:text-[#4ade80] transition-colors text-xs"
            aria-label="Close"
          >
            [x]
          </button>
        </div>

        <div className="p-5 space-y-4">
          {reasons.map((r, i) => (
            <div key={i} className="flex gap-3">
              <span className={`text-xs mt-0.5 ${r.passed ? 'text-[#4ade80]' : 'text-[#3a4a3a]'}`}>
                {r.passed ? '[+]' : '[-]'}
              </span>
              <div>
                <div className={`text-[11px] font-medium ${r.passed ? 'text-[#4ade80]' : 'text-[#4a5a4a]'}`}>
                  {r.criterion}
                </div>
                <p className="text-[11px] text-[#6a7a6a] mt-0.5 leading-relaxed">{r.detail}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="px-5 pb-4">
          <p className="text-[9px] text-[#2a3a2a] leading-relaxed">
            // based on crossover strength, volume, revenue quality, profitability, and valuation. not financial advice.
          </p>
        </div>
      </div>
    </div>
  );
}
