import React from "react";

export default function DivergingBar({ value = 0, label = "ELECTRE", min = -5, max = 5, compact = false }) {
  const numVal = Number(value) || 0;
  const clampedVal = Math.min(Math.max(numVal, min), max);
  
  // Calculate percentage offset from zero center (50%)
  const maxRange = Math.max(Math.abs(min), Math.abs(max)) || 5;
  const pctWidth = (Math.abs(clampedVal) / maxRange) * 50; // Max 50% width from center
  const isPositive = clampedVal >= 0;
  
  const displayVal = numVal > 0 ? `+${numVal}` : `${numVal}`;

  if (compact) {
    return (
      <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-semibold bg-brand-primary/10 text-brand-primary border border-brand-primary/20">
        <span className="text-[10px] text-ink-secondary uppercase">ELECTRE</span>
        <span>{displayVal}</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1 min-w-[140px]">
      <div className="flex items-center justify-between text-xs">
        <span className="font-semibold uppercase tracking-wider text-ink-secondary text-[11px]">{label}</span>
        <span className="font-display font-bold text-sm text-brand-primary">{displayVal}</span>
      </div>
      {/* Centered zero bar track */}
      <div className="relative h-2.5 w-full bg-ink-secondary/15 rounded-full overflow-hidden">
        {/* Center zero line marker */}
        <div className="absolute left-1/2 top-0 bottom-0 w-0.5 bg-ink-secondary/40 z-10" />
        
        {/* Fill bar */}
        {isPositive ? (
          <div
            className="absolute top-0 bottom-0 bg-brand-primary rounded-r-full transition-all duration-500"
            style={{ left: '50%', width: `${pctWidth}%` }}
          />
        ) : (
          <div
            className="absolute top-0 bottom-0 bg-status-warn rounded-l-full transition-all duration-500"
            style={{ right: '50%', width: `${pctWidth}%` }}
          />
        )}
      </div>
    </div>
  );
}
