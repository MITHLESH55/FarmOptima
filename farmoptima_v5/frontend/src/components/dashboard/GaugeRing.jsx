import React from "react";

export default function GaugeRing({ value = 0, label = "TOPSIS", size = 96, strokeWidth = 8 }) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const numericVal = Math.min(Math.max(Number(value) || 0, 0), 1);
  const strokeDashoffset = circumference - numericVal * circumference;

  return (
    <div className="flex flex-col items-center justify-center">
      <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
        <svg className="transform -rotate-90" width={size} height={size}>
          {/* Background track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            className="stroke-brand-primary/15"
            strokeWidth={strokeWidth}
            fill="transparent"
          />
          {/* Progress track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            className="stroke-brand-primary transition-all duration-700 ease-out"
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            fill="transparent"
          />
        </svg>
        {/* Center score */}
        <div className="absolute flex flex-col items-center justify-center text-center">
          <span className="font-display font-bold text-xl tracking-tight text-ink-primary">
            {numericVal.toFixed(4)}
          </span>
        </div>
      </div>
      {label && (
        <span className="text-[11px] font-semibold tracking-wider uppercase text-ink-secondary mt-1">
          {label}
        </span>
      )}
    </div>
  );
}
