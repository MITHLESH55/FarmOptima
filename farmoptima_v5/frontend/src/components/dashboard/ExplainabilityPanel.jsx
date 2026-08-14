import React, { useState } from "react";
import { ChevronDown, ChevronUp, Sparkles, BookOpen, Table } from "lucide-react";
import { t, translateCropName } from "../../i18n";
import { buildExplanation, buildIrrigationSchedule } from "../../utils/statusHelpers";

export default function ExplainabilityPanel({ data, locale }) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!data || !data.crop_ranking || data.crop_ranking.length === 0) return null;

  const top = data.crop_ranking[0];
  const plan = data.resource_plan || {};
  const translatedCrop = translateCropName(top.crop, locale);
  const explanationText = buildExplanation(data, locale);

  const dailyWater = plan.water_liters_per_week ? Math.round(plan.water_liters_per_week / 7).toLocaleString() : "5,153";
  const fertKg = plan.fertilizer_kg_per_acre || "17.4";
  const schedule = buildIrrigationSchedule(plan, locale);

  return (
    <div className="bg-surface rounded-card border border-brand-primary/20 shadow-card overflow-hidden">
      {/* Panel Header */}
      <div className="p-6 bg-brand-primary/5 border-b border-brand-primary/15 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-brand-primary/10 text-brand-primary flex items-center justify-center flex-shrink-0">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-display font-bold text-lg text-ink-primary">
              {t("explain.title", locale)}
            </h3>
            <p className="text-xs text-ink-secondary">
              {t("explain.subtitle", locale)}
            </p>
          </div>
        </div>

        {/* Expand/Collapse Toggle Button */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-surface border border-ink-secondary/20 text-ink-primary font-semibold text-xs hover:bg-base transition-colors flex-shrink-0"
        >
          <span>{isExpanded ? t("explain.hideTechnical", locale) : t("explain.showTechnical", locale)}</span>
          {isExpanded ? <ChevronUp className="w-4 h-4 text-brand-primary" /> : <ChevronDown className="w-4 h-4 text-brand-primary" />}
        </button>
      </div>

      {/* Default State: 2-line plain English summary + Small resource table */}
      <div className="p-6 space-y-6">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-ink-secondary block mb-1">
            {t("explain.summaryOverview", locale)}
          </span>
          <p className="text-sm font-medium text-ink-primary leading-relaxed line-clamp-2">
            {t("explain.summaryText", locale, {
              crop: translatedCrop,
              topsis: typeof top.topsis_closeness === "number" ? top.topsis_closeness.toFixed(3) : top.topsis_closeness,
              electre: top.electre_net_outranking > 0 ? `+${top.electre_net_outranking}` : top.electre_net_outranking
            })}
          </p>
        </div>

        {/* Small Table of Water / Fertilizer / Schedule */}
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-ink-secondary flex items-center gap-1.5 mb-3">
            <Table className="w-3.5 h-3.5 text-brand-primary" />
            {t("explain.inputSummaryTitle", locale)}
          </span>
          <div className="overflow-x-auto border border-ink-secondary/15 rounded-xl">
            <table className="w-full text-left text-xs text-ink-primary">
              <thead className="bg-base border-b border-ink-secondary/15 text-ink-secondary uppercase text-[10px] font-bold tracking-wider">
                <tr>
                  <th className="px-4 py-2.5">{t("explain.colParameter", locale)}</th>
                  <th className="px-4 py-2.5">{t("explain.colTarget", locale)}</th>
                  <th className="px-4 py-2.5">{t("explain.colSchedule", locale)}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-secondary/10">
                <tr className="hover:bg-base/50">
                  <td className="px-4 py-3 font-semibold text-ink-primary flex items-center gap-1.5">
                    {t("explain.irrigationWater", locale)}
                  </td>
                  <td className="px-4 py-3 font-bold text-brand-primary">
                    {t("plan.waterPerDay", locale, { water: dailyWater })}
                  </td>
                  <td className="px-4 py-3 text-ink-secondary">{schedule}</td>
                </tr>
                <tr className="hover:bg-base/50">
                  <td className="px-4 py-3 font-semibold text-ink-primary flex items-center gap-1.5">
                    {t("explain.fertilizerDosageRow", locale)}
                  </td>
                  <td className="px-4 py-3 font-bold text-brand-primary">
                    {t("plan.fertPerAcre", locale, { fert: fertKg })}
                  </td>
                  <td className="px-4 py-3 text-ink-secondary">{t("explain.splitDetail", locale)}</td>
                </tr>
                <tr className="hover:bg-base/50">
                  <td className="px-4 py-3 font-semibold text-ink-primary flex items-center gap-1.5">
                    {t("explain.topCropSelected", locale)}
                  </td>
                  <td className="px-4 py-3 font-bold text-brand-primary">{translatedCrop}</td>
                  <td className="px-4 py-3 text-ink-secondary">{t("explain.seasonDuration", locale)}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Expanded Technical Details */}
        {isExpanded && (
          <div className="pt-6 border-t border-ink-secondary/15 space-y-4 animate-fadeIn">
            <span className="text-xs font-bold uppercase tracking-wider text-brand-primary flex items-center gap-1.5">
              <BookOpen className="w-4 h-4" />
              {t("explain.fullTechnical", locale)}
            </span>
            <div className="p-4 rounded-xl bg-brand-primary/5 border border-brand-primary/20 text-xs text-ink-primary leading-relaxed space-y-2">
              <p>{explanationText}</p>
              <div className="pt-2 text-[11px] text-ink-secondary border-t border-brand-primary/10 grid grid-cols-2 gap-2">
                <div>AHP Consistency Ratio: <strong>{data.ahp_consistency_ratio}</strong></div>
                <div>AHP Method: <strong>{data.ahp_method || "Fuzzy-AHP (Chang Extent)"}</strong></div>
                <div>TOPSIS Rank #1 Closeness: <strong>{top.topsis_closeness}</strong></div>
                <div>ELECTRE Net Outranking: <strong>+{top.electre_net_outranking}</strong></div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

