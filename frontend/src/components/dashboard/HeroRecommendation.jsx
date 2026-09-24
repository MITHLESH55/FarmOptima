import React, { useState } from "react";
import GaugeRing from "./GaugeRing";
import DivergingBar from "./DivergingBar";
import { Droplet, Sprout, Calendar, Info, Award } from "lucide-react";
import { t, translateCropName } from "../../i18n";
import { buildExplanation, buildIrrigationSchedule } from "../../utils/statusHelpers";

export default function HeroRecommendation({ data, loading, locale }) {
  const [showFullWhy, setShowFullWhy] = useState(false);

  if (loading) {
    return (
      <div className="bg-brand-primary/5 border border-brand-primary/20 rounded-card shadow-card p-8 animate-pulse flex items-center justify-center h-[280px]">
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-full bg-brand-primary/20 mx-auto animate-bounce" />
          <span className="text-sm font-semibold text-brand-primary">
            {t("hero.computingTitle", locale)}
          </span>
        </div>
      </div>
    );
  }

  if (!data || !data.crop_ranking || data.crop_ranking.length === 0) {
    return (
      <div className="bg-brand-primary/5 border border-brand-primary/20 rounded-card shadow-card p-8 flex flex-col items-center justify-center text-center h-[240px]">
        <Award className="w-10 h-10 text-brand-accent mb-3" />
        <h2 className="font-display text-2xl font-bold text-ink-primary">
          {t("hero.emptyTitle", locale)}
        </h2>
        <p className="text-sm text-ink-secondary max-w-lg mt-1">
          {t("hero.emptySubtitle", locale)}
        </p>
      </div>
    );
  }

  const top = data.crop_ranking[0];
  const plan = data.resource_plan || {};
  const topsisScore = top.topsis_closeness || 0;
  const electreScore = top.electre_net_outranking || 0;
  const translatedCrop = translateCropName(top.crop, locale);

  // Format daily water and fertilizer stat chips
  const dailyWater = plan.water_liters_per_week ? Math.round(plan.water_liters_per_week / 7).toLocaleString() : "5,153";
  const fertPerAcre = plan.fertilizer_kg_per_acre || "17.4";
  const scheduleText = buildIrrigationSchedule(plan, locale);

  const whySummary = buildExplanation(data, locale);

  const nut = data?.fertilizer_plan?.nutrient_requirements;
  const fertDisplay = nut
    ? `🌱 N-P-K: ${nut.nitrogen_kg_per_acre}-${nut.phosphorus_kg_per_acre}-${nut.potassium_kg_per_acre} kg/ac`
    : t("plan.fertPerAcre", locale, { fert: fertPerAcre });

  return (
    <div className="bg-brand-primary/5 border border-brand-primary/20 rounded-card shadow-card p-8 transition-all hover:border-brand-primary/30">
      {/* Top Banner Chip */}
      <div className="flex items-center justify-between mb-4">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-primary text-surface text-xs font-semibold tracking-wide uppercase shadow-sm">
          <Award className="w-3.5 h-3.5 text-brand-accent" />
          <span>{t("hero.topRecommendedCrop", locale)}</span>
        </div>
        <span className="text-xs font-semibold text-ink-secondary bg-surface/80 px-2.5 py-1 rounded-md border border-ink-secondary/15">
          {t("hero.rankAnalyzed", locale, { total: data.crop_ranking.length })}
        </span>
      </div>

      {/* Main Grid: Gauge + Crop Name/Scores/Why */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
        {/* Left Column: GaugeRing (TOPSIS) */}
        <div className="md:col-span-3 flex justify-center md:justify-start">
          <GaugeRing value={topsisScore} label={t("hero.topsisCloseness", locale)} size={110} strokeWidth={9} />
        </div>

        {/* Center/Right Column: Crop Title, ELECTRE Bar, Why statement */}
        <div className="md:col-span-9 space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-baseline gap-4 justify-between">
            {/* Crop Name */}
            <h2 className="font-display font-extrabold text-4xl text-ink-primary tracking-tight">
              {translatedCrop}
            </h2>
            
            {/* ELECTRE DivergingBar */}
            <div className="flex-shrink-0">
              <DivergingBar value={electreScore} label={t("hero.electreRank", locale)} min={-5} max={5} />
            </div>
          </div>

          {/* Why Summary (Max 2 lines with tooltip/toggle) */}
          <div className="relative bg-surface/80 rounded-lg p-3 border border-ink-secondary/15">
            <div className="flex items-start gap-2">
              <Info className="w-4 h-4 text-brand-primary flex-shrink-0 mt-0.5" />
              <div className="text-xs text-ink-primary flex-1">
                <span className="font-semibold text-brand-primary mr-1">
                  {t("hero.whyThisCrop", locale)}
                </span>
                <span className={showFullWhy ? "" : "line-clamp-2"}>
                  {whySummary}
                </span>
                {whySummary.length > 120 && (
                  <button
                    onClick={() => setShowFullWhy(!showFullWhy)}
                    className="ml-1 text-[11px] font-bold text-brand-primary underline hover:text-brand-accent transition-colors"
                  >
                    {showFullWhy ? t("hero.showLess", locale) : t("hero.readRationale", locale)}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Row: Stat Chips */}
      <div className="mt-6 pt-5 border-t border-brand-primary/15 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-surface border border-brand-primary/20 shadow-sm text-xs font-semibold text-ink-primary">
          <Droplet className="w-4 h-4 text-criterion-water" />
          <span>{t("plan.waterPerDay", locale, { water: dailyWater })}</span>
        </div>

        <div className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-surface border border-brand-primary/20 shadow-sm text-xs font-semibold text-ink-primary">
          <Sprout className="w-4 h-4 text-status-good" />
          <span>{fertDisplay}</span>
        </div>

        <div className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-surface border border-brand-primary/20 shadow-sm text-xs font-semibold text-ink-primary">
          <Calendar className="w-4 h-4 text-brand-accent" />
          <span>📅 {scheduleText}</span>
        </div>
      </div>
    </div>
  );
}

