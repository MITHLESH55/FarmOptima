import React from "react";
import { t } from "../../i18n";

export default function RangeBand({ value, rangeMin, rangeMax, minScale = 0, maxScale = 50, locale }) {
  const hasRange = rangeMin !== undefined && rangeMin !== null && rangeMax !== undefined && rangeMax !== null;
  const numVal = Number(value);
  const isValueValid = !isNaN(numVal) && value !== null;

  if (!hasRange || !isValueValid) {
    return (
      <div 
        className="w-full mt-2" 
        title={t("status.noRefRange", locale)}
      >
        <div className="flex justify-between text-[10px] text-ink-secondary/70 mb-1">
          <span>{t("status.track", locale)}</span>
          <span className="italic">{t("status.noRefShort", locale)}</span>
        </div>
        <div className="relative h-2 w-full bg-ink-secondary/15 rounded-full overflow-hidden">
          <div className="absolute top-0 bottom-0 left-0 right-0 bg-ink-secondary/10" />
        </div>
      </div>
    );
  }

  const rMin = Number(rangeMin);
  const rMax = Number(rangeMax);

  // Compute adaptive min/max for visual track
  const trackMin = Math.min(rMin * 0.7, minScale, numVal < rMin ? numVal * 0.9 : rMin);
  const trackMax = Math.max(rMax * 1.3, maxScale, numVal > rMax ? numVal * 1.1 : rMax);
  const span = (trackMax - trackMin) || 1;

  // Percentages for range band and dot
  const bandLeftPct = Math.max(0, Math.min(100, ((rMin - trackMin) / span) * 100));
  const bandRightPct = Math.max(0, Math.min(100, ((rMax - trackMin) / span) * 100));
  const bandWidthPct = Math.max(0, bandRightPct - bandLeftPct);

  const dotPct = Math.max(2, Math.min(98, ((numVal - trackMin) / span) * 100));

  const isInside = numVal >= rMin && numVal <= rMax;
  const dotColorClass = isInside ? "bg-status-good ring-status-good/30" : "bg-status-risk ring-status-risk/30";

  return (
    <div className="w-full mt-2" title={`Ideal: ${rMin} - ${rMax} | Measured: ${numVal}`}>
      <div className="flex justify-between text-[10px] font-medium text-ink-secondary mb-1">
        <span>{t("status.ideal", locale, { min: rMin, max: rMax })}</span>
        <span className={isInside ? "text-status-good font-semibold" : "text-status-risk font-semibold"}>
          {isInside ? t("status.optimal", locale) : t("status.outOfRange", locale)}
        </span>
      </div>
      
      <div className="relative h-2.5 w-full bg-ink-secondary/15 rounded-full">
        {/* Ideal range shaded band */}
        <div
          className="absolute top-0 bottom-0 bg-status-good/25 rounded-sm border-x border-status-good/40"
          style={{ left: `${bandLeftPct}%`, width: `${bandWidthPct}%` }}
        />

        {/* Live value marker */}
        <div
          className={`absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-3.5 h-3.5 rounded-full border-2 border-surface shadow-sm ring-2 ${dotColorClass} transition-all duration-300 z-10`}
          style={{ left: `${dotPct}%` }}
        />
      </div>
    </div>
  );
}
