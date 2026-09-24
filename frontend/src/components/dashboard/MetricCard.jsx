import React from "react";
import RangeBand from "./RangeBand";
import { t } from "../../i18n";

function SourceBadge({ source, locale }) {
  if (!source) return null;

  let badgeText = t("status.liveBadge", locale);
  let bgClass = "bg-brand-primary/10 text-brand-primary border-brand-primary/20";
  let title = `${t("status.sourceData", locale)}: ${source}`;

  if (source === "soilgrids") {
    badgeText = "MODEL";
    bgClass = "bg-indigo-500/10 text-indigo-600 border-indigo-500/20";
    title = "ISRIC SoilGrids v2.0 Model Prediction";
  } else if (source === "lab_measurement") {
    badgeText = "LAB";
    bgClass = "bg-emerald-500/10 text-emerald-600 border-emerald-500/20";
    title = "Verified Laboratory Soil Sample";
  } else if (typeof source === "string" && source.includes("cached")) {
    badgeText = "CACHED";
    bgClass = "bg-amber-500/10 text-amber-600 border-amber-500/20";
    title = "Cached Historical Observation";
  } else if (source === "mock") {
    badgeText = t("status.mockBadge", locale);
    bgClass = "bg-brand-accent/15 text-brand-accent border-brand-accent/30";
    title = t("status.mockFallback", locale);
  } else if (source === "unavailable") {
    badgeText = t("status.naBadge", locale);
    bgClass = "bg-status-risk/15 text-status-risk border-status-risk/30";
    title = t("status.serviceUnavailable", locale);
  }

  return (
    <span
      className={`text-[9px] font-bold tracking-wider px-1.5 py-0.5 rounded border uppercase ${bgClass}`}
      title={title}
    >
      {badgeText}
    </span>
  );
}


export default function MetricCard({
  icon,
  label,
  value,
  unit = "",
  rangeMin,
  rangeMax,
  liveBadge,
  minScale,
  maxScale,
  subtext,
  locale,
}) {
  const isUnavailable = liveBadge === "unavailable" || value === null || value === undefined;
  const displayVal = isUnavailable ? "—" : value;

  return (
    <div className="bg-surface rounded-card border border-ink-secondary/15 p-4 shadow-sm flex flex-col justify-between hover:shadow-card transition-shadow">
      <div>
        {/* Header row with icon + label + badge */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            {icon && <div className="text-brand-primary text-base flex-shrink-0">{icon}</div>}
            <span className="text-xs font-semibold text-ink-secondary tracking-wide truncate">
              {label}
            </span>
          </div>
          <SourceBadge source={liveBadge} locale={locale} />
        </div>

        {/* Value + Unit */}
        <div className="flex items-baseline gap-1 my-1">
          <span className="text-2xl font-bold font-body text-ink-primary tracking-tight">
            {displayVal}
          </span>
          {unit && <span className="text-xs font-normal text-ink-secondary">{unit}</span>}
        </div>

        {subtext && (
          <p className="text-[11px] text-ink-secondary/80 mt-0.5 leading-tight">{subtext}</p>
        )}
      </div>

      {/* RangeBand track indicator */}
      <RangeBand
        value={value}
        rangeMin={rangeMin}
        rangeMax={rangeMax}
        minScale={minScale}
        maxScale={maxScale}
        locale={locale}
      />
    </div>
  );
}
