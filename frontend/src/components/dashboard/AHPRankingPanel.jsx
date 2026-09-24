import React from "react";
import DivergingBar from "./DivergingBar";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from "recharts";
import { CheckCircle2, AlertTriangle, Scale, Trophy } from "lucide-react";
import { t, translateCropName } from "../../i18n";


export default function AHPRankingPanel({ data, locale }) {
  if (!data) return null;

  const weights = data.ahp_weights || {
    climate_suitability: 0.4495,
    soil_suitability: 0.2596,
    water_efficiency: 0.1707,
    market_value: 0.1202,
  };

  const cr = data.ahp_consistency_ratio || 0.04;
  const isConsistent = data.ahp_is_consistent !== false;

  // Criterion tokens and labels matching backend key names
  const criteriaConfig = [
    {
      key: "climate_suitability",
      label: t("ahp.climate", locale),
      color: "#4C8C5F",
      weight: weights.climate_suitability ?? weights.climate ?? 0,
    },
    {
      key: "soil_suitability",
      label: t("ahp.soil", locale),
      color: "#8B6A4A",
      weight: weights.soil_suitability ?? weights.soil ?? weights.soil_quality ?? 0,
    },
    {
      key: "water_efficiency",
      label: t("ahp.water", locale),
      color: "#3E7FA6",
      weight: weights.water_efficiency ?? weights.water ?? weights.water_availability ?? 0,
    },
    {
      key: "market_value",
      label: t("ahp.market", locale),
      color: "#A9752E",
      weight: weights.market_value ?? weights.market ?? weights.market_economic ?? 0,
    },
  ];

  const totalWeight = criteriaConfig.reduce((acc, c) => acc + c.weight, 0) || 1;

  // Prepare data for Recharts horizontal bar chart (layout="vertical")
  const chartData = (data.crop_ranking || []).map((item) => ({
    cropOriginal: item.crop,
    crop: translateCropName(item.crop, locale),
    topsis: item.topsis_closeness,
    electre: item.electre_net_outranking,
    rank: item.rank,
  }));

  return (
    <div className="space-y-8">
      {/* 1. AHP Criteria Weights (Single 100%-stacked bar chart + Legend) */}
      <div className="bg-surface rounded-card border border-ink-secondary/15 p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          <div>
            <h3 className="font-display font-bold text-lg text-ink-primary flex items-center gap-2">
              <Scale className="w-5 h-5 text-brand-primary" />
              {t("ahp.title", locale)}
            </h3>
            <p className="text-xs text-ink-secondary mt-0.5">
              {t("ahp.subtitle", locale)}
            </p>
          </div>

          {/* Consistency Ratio Badge */}
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-base border border-ink-secondary/15 text-xs font-semibold">
            <span>{t("ahp.consistencyRatio", locale, { cr })}</span>
            {isConsistent ? (
              <span className="text-status-good flex items-center gap-1">
                <CheckCircle2 className="w-4 h-4" /> {t("ahp.consistent", locale)}
              </span>
            ) : (
              <span className="text-status-risk flex items-center gap-1">
                <AlertTriangle className="w-4 h-4" /> {t("ahp.inconsistent", locale)}
              </span>
            )}
          </div>
        </div>

        {/* ONE Horizontal 100%-stacked bar */}
        <div className="w-full h-7 rounded-xl overflow-hidden flex shadow-inner border border-ink-secondary/20">
          {criteriaConfig.map((item) => {
            const pct = ((item.weight / totalWeight) * 100).toFixed(1);
            return (
              <div
                key={item.key}
                style={{ width: `${pct}%`, backgroundColor: item.color }}
                className="h-full transition-all duration-500 relative group flex items-center justify-center"
                title={`${item.label}: ${pct}%`}
              >
                {Number(pct) > 8 && (
                  <span className="text-[11px] font-bold text-surface drop-shadow-sm">
                    {pct}%
                  </span>
                )}
              </div>
            );
          })}
        </div>

        {/* Criteria Legend Below Stacked Bar */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-5 pt-4 border-t border-ink-secondary/15">
          {criteriaConfig.map((item) => {
            const pct = ((item.weight / totalWeight) * 100).toFixed(1);
            return (
              <div key={item.key} className="flex items-center gap-2.5">
                <div
                  className="w-3.5 h-3.5 rounded-md flex-shrink-0"
                  style={{ backgroundColor: item.color }}
                />
                <div className="flex flex-col text-xs">
                  <span className="font-semibold text-ink-primary">{item.label}</span>
                  <span className="text-ink-secondary font-medium">{pct}% ({item.weight.toFixed(3)})</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 2. Crop Ranking Horizontal Bar Chart (Recharts) */}
      <div className="bg-surface rounded-card border border-ink-secondary/15 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="font-display font-bold text-lg text-ink-primary flex items-center gap-2">
              <Trophy className="w-5 h-5 text-brand-accent" />
              {t("ranking.title", locale)}
            </h3>
            <p className="text-xs text-ink-secondary mt-0.5">
              {t("ranking.subtitle", locale)}
            </p>
          </div>
        </div>

        {/* Horizontal Bar Chart (Recharts layout="vertical") */}
        <div className="w-full h-[320px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              layout="vertical"
              data={chartData}
              margin={{ top: 10, right: 30, left: 40, bottom: 10 }}
            >
              <XAxis type="number" domain={[0, 1]} tickCount={6} stroke="#5B6B60" fontSize={12} />
              <YAxis
                type="category"
                dataKey="crop"
                stroke="#14251C"
                fontSize={13}
                fontWeight={600}
                width={100}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const dataPoint = payload[0].payload;
                    return (
                      <div className="bg-surface p-3 rounded-lg border border-ink-secondary/20 shadow-lg text-xs space-y-1">
                        <div className="font-bold text-ink-primary text-sm">{dataPoint.crop}</div>
                        <div>{t("dashboard.rank", locale)}: <strong>#{dataPoint.rank}</strong></div>
                        <div>{t("dashboard.topsis", locale)} {t("dashboard.score", locale)}: <strong>{dataPoint.topsis}</strong></div>
                        <div>{t("dashboard.electre", locale)}: <strong>+{dataPoint.electre}</strong></div>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Bar dataKey="topsis" radius={[0, 8, 8, 0]} barSize={24}>
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={index === 0 ? "#2E6B4F" : "rgba(91, 107, 96, 0.3)"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Detailed Crop Rank List with Inline ELECTRE Chips & Auditable Table */}
        <div className="mt-8 space-y-4 pt-6 border-t border-ink-secondary/15">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-ink-secondary block">
                {t("ranking.matrixTitle", locale)}
              </span>
              <p className="text-[11px] text-ink-secondary mt-0.5">
                Auditable breakdown: Criterion Scores (0–1), TOPSIS Distance Closeness ($C_i^*$), and ELECTRE-I Net Outranking ($O_i - \bar{O}_i$).
              </p>
            </div>
          </div>

          {/* Full Auditable Criteria Matrix & Performance Table */}
          <div className="overflow-x-auto rounded-xl border border-ink-secondary/15 bg-base">
            <table className="w-full text-left text-xs">
              <thead className="bg-surface border-b border-ink-secondary/15 text-ink-secondary uppercase text-[10px] font-bold tracking-wider">
                <tr>
                  <th className="py-3 px-3.5 text-center">{t("dashboard.rank", locale)}</th>
                  <th className="py-3 px-3.5">{t("explain.topCropSelected", locale) || "Crop Alternative"}</th>
                  <th className="py-3 px-3 text-right" title={`Weight: ${(weights.climate_suitability ?? weights.climate ?? 0.45).toFixed(3)}`}>
                    <span className="text-[#4C8C5F]">Climate</span>
                    <span className="block text-[9px] font-normal text-ink-secondary">w={((weights.climate_suitability ?? weights.climate ?? 0.45) * 100).toFixed(0)}%</span>
                  </th>
                  <th className="py-3 px-3 text-right" title={`Weight: ${(weights.soil_suitability ?? weights.soil ?? 0.26).toFixed(3)}`}>
                    <span className="text-[#8B6A4A]">Soil</span>
                    <span className="block text-[9px] font-normal text-ink-secondary">w={((weights.soil_suitability ?? weights.soil ?? 0.26) * 100).toFixed(0)}%</span>
                  </th>
                  <th className="py-3 px-3 text-right" title={`Weight: ${(weights.water_efficiency ?? weights.water ?? 0.17).toFixed(3)}`}>
                    <span className="text-[#3E7FA6]">Water</span>
                    <span className="block text-[9px] font-normal text-ink-secondary">w={((weights.water_efficiency ?? weights.water ?? 0.17) * 100).toFixed(0)}%</span>
                  </th>
                  <th className="py-3 px-3 text-right" title={`Weight: ${(weights.market_value ?? weights.market ?? 0.12).toFixed(3)}`}>
                    <span className="text-[#A9752E]">Market</span>
                    <span className="block text-[9px] font-normal text-ink-secondary">w={((weights.market_value ?? weights.market ?? 0.12) * 100).toFixed(0)}%</span>
                  </th>
                  <th className="py-3 px-3.5 text-right font-bold text-brand-primary">TOPSIS Closeness</th>
                  <th className="py-3 px-3.5 text-right font-bold text-ink-primary">ELECTRE Net</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-secondary/10 font-medium text-ink-primary">
                {(data.crop_ranking || []).map((c) => {
                  const crit = c.criteria_scores || {};
                  return (
                    <tr
                      key={c.crop}
                      className={`hover:bg-surface/60 transition-colors ${
                        c.rank === 1 ? "bg-brand-primary/5 font-semibold" : ""
                      }`}
                    >
                      <td className="py-2.5 px-3.5 text-center">
                        <span
                          className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${
                            c.rank === 1
                              ? "bg-brand-primary text-surface shadow-xs"
                              : "bg-ink-secondary/15 text-ink-primary"
                          }`}
                        >
                          #{c.rank}
                        </span>
                      </td>
                      <td className="py-2.5 px-3.5 font-bold text-ink-primary">
                        {translateCropName(c.crop, locale)}
                        {c.rank === 1 && (
                          <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-brand-primary/15 text-brand-primary font-bold">
                            RECOMMENDED
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-ink-secondary">
                        {crit.climate_suitability !== undefined ? crit.climate_suitability.toFixed(3) : "—"}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-ink-secondary">
                        {crit.soil_suitability !== undefined ? crit.soil_suitability.toFixed(3) : "—"}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-ink-secondary">
                        {crit.water_efficiency !== undefined ? crit.water_efficiency.toFixed(3) : "—"}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-ink-secondary">
                        {crit.market_value !== undefined ? crit.market_value.toFixed(3) : "—"}
                      </td>
                      <td className="py-2.5 px-3.5 text-right font-mono font-bold text-brand-primary">
                        {typeof c.topsis_closeness === "number" ? c.topsis_closeness.toFixed(4) : c.topsis_closeness}
                      </td>
                      <td className="py-2.5 px-3.5 text-right">
                        <DivergingBar value={c.electre_net_outranking} compact locale={locale} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="p-3.5 rounded-xl bg-surface border border-ink-secondary/15 text-[11px] text-ink-secondary space-y-1">
            <div className="font-semibold text-ink-primary">Mathematical Decision Formulation:</div>
            <div>• <strong>AHP Weights:</strong> Derived from pairwise comparison eigenvector analysis (CR = {cr}).</div>
            <div>• <strong>TOPSIS Closeness:</strong> C_i = D_i^- / (D_i^+ + D_i^-) in [0, 1], where D_i^+ is Euclidean distance to the ideal-best profile and D_i^- is distance to ideal-worst.</div>
            <div>• <strong>ELECTRE-I Net Score:</strong> O_i - Ō_i = (candidates i outranks) - (candidates that outrank i) under concordance threshold c=0.6, discordance d=0.4.</div>
          </div>
        </div>
      </div>
    </div>
  );
}

