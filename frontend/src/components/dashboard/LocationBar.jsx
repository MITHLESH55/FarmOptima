import React from "react";
import { MapPin, RefreshCw, Compass } from "lucide-react";
import { t } from "../../i18n";

export default function LocationBar({ position, onOpenMap, onGetRecommendation, loading, locale }) {
  return (
    <div className="w-full bg-surface border-b border-ink-secondary/15 shadow-sm py-4">
      <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Left side: Map Icon + Coords info */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-brand-primary/10 flex items-center justify-center text-brand-primary flex-shrink-0">
            <Compass className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-ink-secondary">
                {t("header.targetLocation", locale)}
              </span>
              {position && (
                <span className="text-[10px] bg-brand-primary/10 text-brand-primary font-bold px-2 py-0.5 rounded-full">
                  {t("header.selected", locale)}
                </span>
              )}
            </div>
            <div className="text-sm font-bold text-ink-primary flex items-center gap-1.5 mt-0.5">
              <MapPin className="w-4 h-4 text-brand-accent flex-shrink-0" />
              {position ? (
                <span>
                  {position.lat.toFixed(4)}° N, {position.lon.toFixed(4)}° E
                </span>
              ) : (
                <span className="text-ink-secondary font-normal italic">
                  {t("header.noLocationSet", locale)}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Right side: Action Buttons */}
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <button
            onClick={onOpenMap}
            className="flex-1 sm:flex-none px-4 py-2.5 rounded-lg border border-ink-secondary/25 bg-surface text-ink-primary font-medium text-sm hover:bg-base hover:border-ink-secondary/40 transition-colors flex items-center justify-center gap-2"
          >
            <MapPin className="w-4 h-4 text-brand-primary" />
            <span>{t("header.changeLocation", locale)}</span>
          </button>

          <button
            onClick={onGetRecommendation}
            disabled={!position || loading}
            className="flex-1 sm:flex-none px-6 py-2.5 rounded-lg bg-brand-primary text-surface font-semibold text-sm hover:bg-brand-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-sm flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>{t("header.computing", locale)}</span>
              </>
            ) : (
              <>
                <span>{t("header.getRecommendation", locale)}</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
