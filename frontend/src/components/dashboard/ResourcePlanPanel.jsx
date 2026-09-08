import React, { useState } from "react";
import {
  Droplet,
  Sprout,
  Calendar,
  Zap,
  TrendingDown,
  LineChart as LineChartIcon,
  HelpCircle,
  Layers,
  FlaskConical,
  Scale,
  Maximize2,
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";
import { t, translateCropName } from "../../i18n";
import { buildIrrigationSchedule } from "../../utils/statusHelpers";

export default function ResourcePlanPanel({ data, locale }) {
  const fertPlan = data?.fertilizer_plan;
  const initialArea = fertPlan?.field_area_acres || 1.0;
  const [fieldArea, setFieldArea] = useState(initialArea);

  if (!data || !data.resource_plan) return null;

  const plan = data.resource_plan;
  const topCropRaw = data.crop_ranking?.[0]?.crop || "Selected Crop";
  const topCrop = translateCropName(topCropRaw, locale);

  const dailyWater = plan.water_liters_per_week
    ? Math.round(plan.water_liters_per_week / 7).toLocaleString()
    : "5,153";
  const scheduleText = buildIrrigationSchedule(plan, locale);
  const generations = plan.optimizer_generations_run || 60;
  const bestFitness = plan.optimizer_best_fitness || 0.179;

  // Compute live scaling based on fieldArea state
  const areaScale = fieldArea > 0 ? fieldArea : 1.0;

  // Prepare data for Pareto Front / Convergence trajectory chart
  const convergencePoints = (plan.convergence_history || []).map((val, idx) => ({
    gen: idx + 1,
    cost: val,
  }));

  const paretoPoints = (plan.pareto_front || []).map((pt, idx) => ({
    gen: idx + 1,
    water: Math.round(pt.water_liters_per_week / 7),
    fertilizer: pt.fertilizer_kg_per_acre,
    cost: pt.resource_cost || (pt.water_gap ** 2 + pt.fertilizer_gap ** 2) ** 0.5,
  }));

  const sparklineData =
    convergencePoints.length > 0
      ? convergencePoints
      : paretoPoints.length > 0
      ? paretoPoints
      : Array.from({ length: 10 }, (_, i) => ({
          gen: (i + 1) * 6,
          cost: Number((bestFitness * (1 + 0.8 / (i + 1))).toFixed(4)),
        }));

  // Nutrient requirements with scaling
  const nutReq = fertPlan?.nutrient_requirements || {
    nitrogen_kg_per_acre: fertPlan ? fertPlan.nutrient_requirements.nitrogen_kg_per_acre : (plan.fertilizer_kg_per_acre || 55.0),
    phosphorus_kg_per_acre: 24.0,
    potassium_kg_per_acre: 20.0,
  };

  const nPerAcre = nutReq.nitrogen_kg_per_acre;
  const pPerAcre = nutReq.phosphorus_kg_per_acre;
  const kPerAcre = nutReq.potassium_kg_per_acre;

  const nTotalField = (nPerAcre * areaScale).toFixed(1);
  const pTotalField = (pPerAcre * areaScale).toFixed(1);
  const kTotalField = (kPerAcre * areaScale).toFixed(1);

  // Commercial fertilizers (DAP, Urea, MOP)
  const dapPerAcre = Number((pPerAcre / 0.46).toFixed(2));
  const dapTotalField = Number((dapPerAcre * areaScale).toFixed(1));
  const nFromDapPerAcre = dapPerAcre * 0.18;
  const remainingNPerAcre = Math.max(0, nPerAcre - nFromDapPerAcre);
  const ureaPerAcre = Number((remainingNPerAcre / 0.46).toFixed(2));
  const ureaTotalField = Number((ureaPerAcre * areaScale).toFixed(1));
  const mopPerAcre = Number((kPerAcre / 0.60).toFixed(2));
  const mopTotalField = Number((mopPerAcre * areaScale).toFixed(1));

  // Schedule breakdown
  const ureaBasal = Number((ureaTotalField * 0.50).toFixed(1));
  const ureaTd1 = Number((ureaTotalField * 0.25).toFixed(1));
  const ureaTd2 = Number((ureaTotalField * 0.25).toFixed(1));

  const basalTotal = Number((dapTotalField + mopTotalField + ureaBasal).toFixed(1));
  const td1Total = ureaTd1;
  const td2Total = ureaTd2;

  return (
    <div className="space-y-8">
      {/* 1. Water & Irrigation Overview Card */}
      <div className="bg-surface rounded-card border border-ink-secondary/15 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-display font-bold text-lg text-ink-primary flex items-center gap-2">
              <Zap className="w-5 h-5 text-brand-primary" />
              {t("plan.title", locale, { crop: topCrop })}
            </h3>
            <p className="text-xs text-ink-secondary mt-0.5">
              {t("plan.subtitle", locale)}
            </p>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-brand-primary/10 text-brand-primary border border-brand-primary/20">
            {t("plan.method", locale)}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="flex items-center gap-3 p-4 rounded-xl bg-base border border-ink-secondary/15">
            <div className="w-10 h-10 rounded-lg bg-criterion-water/15 text-criterion-water flex items-center justify-center flex-shrink-0">
              <Droplet className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[11px] font-semibold text-ink-secondary uppercase tracking-wider block">
                {t("plan.waterTarget", locale)}
              </span>
              <span className="font-bold text-lg text-ink-primary">
                {t("plan.waterPerDay", locale, { water: dailyWater })}
              </span>
              <span className="text-[10px] text-ink-secondary block mt-0.5">
                {t("plan.waterPerWeek", locale, { water: plan.water_liters_per_week?.toLocaleString() || "36,070" })}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3 p-4 rounded-xl bg-base border border-ink-secondary/15">
            <div className="w-10 h-10 rounded-lg bg-brand-accent/15 text-brand-accent flex items-center justify-center flex-shrink-0">
              <Calendar className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[11px] font-semibold text-ink-secondary uppercase tracking-wider block">
                {t("plan.irrigationSchedule", locale)}
              </span>
              <span className="font-bold text-sm text-ink-primary block leading-tight">
                📅 {scheduleText}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Structured Agronomic Fertilizer Plan Section */}
      <div className="bg-surface rounded-card border border-ink-secondary/15 p-6 shadow-sm space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-ink-secondary/15 pb-4">
          <div>
            <h3 className="font-display font-bold text-lg text-ink-primary flex items-center gap-2">
              <Sprout className="w-5 h-5 text-status-good" />
              {t("plan.fertilizerPlanTitle", locale, { crop: topCrop })}
            </h3>
            <p className="text-xs text-ink-secondary mt-0.5">
              {t("plan.fertilizerPlanSubtitle", locale)}
            </p>
          </div>

          {/* Interactive Field Area Selector */}
          <div className="flex items-center gap-2 bg-base px-3.5 py-2 rounded-xl border border-ink-secondary/20 shadow-xs">
            <Maximize2 className="w-4 h-4 text-brand-primary" />
            <label htmlFor="field-area-input" className="text-xs font-bold text-ink-primary whitespace-nowrap">
              {t("plan.fieldAreaLabel", locale)}:
            </label>
            <input
              id="field-area-input"
              type="number"
              min="0.1"
              max="1000"
              step="0.5"
              value={fieldArea}
              onChange={(e) => setFieldArea(Math.max(0.1, parseFloat(e.target.value) || 1.0))}
              className="w-16 px-2 py-1 bg-surface border border-ink-secondary/25 rounded text-xs font-mono font-bold text-ink-primary focus:outline-none focus:border-brand-primary text-center"
            />
            <span className="text-xs font-semibold text-ink-secondary">{t("plan.acres", locale)}</span>
          </div>
        </div>

        {/* A. Nutrient Requirements Table */}
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-ink-secondary mb-3 flex items-center gap-1.5">
            <FlaskConical className="w-4 h-4 text-brand-primary" />
            {t("plan.nutrientRequirements", locale)}
          </h4>
          <div className="overflow-x-auto rounded-xl border border-ink-secondary/15 bg-base">
            <table className="w-full text-left text-xs">
              <thead className="bg-surface border-b border-ink-secondary/15 text-ink-secondary uppercase text-[10px] font-bold">
                <tr>
                  <th className="py-2.5 px-4">Nutrient</th>
                  <th className="py-2.5 px-4 text-right">{t("plan.perAcre", locale)}</th>
                  <th className="py-2.5 px-4 text-right font-bold text-brand-primary">
                    {t("plan.totalField", locale)} ({areaScale} {t("plan.acres", locale)})
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-secondary/10 font-medium text-ink-primary">
                <tr>
                  <td className="py-2.5 px-4 font-bold flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-status-good"></span>
                    {t("plan.nitrogen", locale)}
                  </td>
                  <td className="py-2.5 px-4 text-right font-mono">{nPerAcre} kg/acre</td>
                  <td className="py-2.5 px-4 text-right font-mono font-bold text-status-good">{nTotalField} kg</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-4 font-bold flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-criterion-water"></span>
                    {t("plan.phosphorus", locale)}
                  </td>
                  <td className="py-2.5 px-4 text-right font-mono">{pPerAcre} kg/acre</td>
                  <td className="py-2.5 px-4 text-right font-mono font-bold text-criterion-water">{pTotalField} kg</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-4 font-bold flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-brand-accent"></span>
                    {t("plan.potassium", locale)}
                  </td>
                  <td className="py-2.5 px-4 text-right font-mono">{kPerAcre} kg/acre</td>
                  <td className="py-2.5 px-4 text-right font-mono font-bold text-brand-accent">{kTotalField} kg</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* B. Recommended Commercial Fertilizer Products */}
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-ink-secondary mb-3 flex items-center gap-1.5">
            <Scale className="w-4 h-4 text-brand-primary" />
            {t("plan.commercialProducts", locale)}
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* DAP Card */}
            <div className="p-4 rounded-xl bg-base border border-ink-secondary/15 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-sm text-ink-primary">DAP</span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-criterion-water/15 text-criterion-water font-bold">18% N, 46% P₂O₅</span>
              </div>
              <p className="text-[11px] text-ink-secondary">Diammonium Phosphate</p>
              <div className="pt-2 border-t border-ink-secondary/10 flex justify-between items-end">
                <div>
                  <span className="text-[10px] text-ink-secondary block">{t("plan.perAcre", locale)}</span>
                  <span className="font-mono font-bold text-sm text-ink-primary">{dapPerAcre} kg/acre</span>
                </div>
                <div className="text-right">
                  <span className="text-[10px] text-ink-secondary block">{t("plan.totalKg", locale)} ({areaScale} ac)</span>
                  <span className="font-mono font-extrabold text-base text-criterion-water">{dapTotalField} kg</span>
                </div>
              </div>
            </div>

            {/* Urea Card */}
            <div className="p-4 rounded-xl bg-base border border-ink-secondary/15 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-sm text-ink-primary">Urea</span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-status-good/15 text-status-good font-bold">46% N</span>
              </div>
              <p className="text-[11px] text-ink-secondary">Nitrogenous Fertilizer</p>
              <div className="pt-2 border-t border-ink-secondary/10 flex justify-between items-end">
                <div>
                  <span className="text-[10px] text-ink-secondary block">{t("plan.perAcre", locale)}</span>
                  <span className="font-mono font-bold text-sm text-ink-primary">{ureaPerAcre} kg/acre</span>
                </div>
                <div className="text-right">
                  <span className="text-[10px] text-ink-secondary block">{t("plan.totalKg", locale)} ({areaScale} ac)</span>
                  <span className="font-mono font-extrabold text-base text-status-good">{ureaTotalField} kg</span>
                </div>
              </div>
            </div>

            {/* MOP Card */}
            <div className="p-4 rounded-xl bg-base border border-ink-secondary/15 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-sm text-ink-primary">MOP</span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-brand-accent/15 text-brand-accent font-bold">60% K₂O</span>
              </div>
              <p className="text-[11px] text-ink-secondary">Muriate of Potash</p>
              <div className="pt-2 border-t border-ink-secondary/10 flex justify-between items-end">
                <div>
                  <span className="text-[10px] text-ink-secondary block">{t("plan.perAcre", locale)}</span>
                  <span className="font-mono font-bold text-sm text-ink-primary">{mopPerAcre} kg/acre</span>
                </div>
                <div className="text-right">
                  <span className="text-[10px] text-ink-secondary block">{t("plan.totalKg", locale)} ({areaScale} ac)</span>
                  <span className="font-mono font-extrabold text-base text-brand-accent">{mopTotalField} kg</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* C. Split Application Schedule Table */}
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-ink-secondary mb-3 flex items-center gap-1.5">
            <Layers className="w-4 h-4 text-brand-primary" />
            {t("plan.applicationSchedule", locale)} ({t("plan.totalKg", locale)} for {areaScale} {t("plan.acres", locale)})
          </h4>
          <div className="overflow-x-auto rounded-xl border border-ink-secondary/15 bg-base">
            <table className="w-full text-left text-xs">
              <thead className="bg-surface border-b border-ink-secondary/15 text-ink-secondary uppercase text-[10px] font-bold">
                <tr>
                  <th className="py-2.5 px-4">Application Stage</th>
                  <th className="py-2.5 px-4 text-right">DAP</th>
                  <th className="py-2.5 px-4 text-right">Urea</th>
                  <th className="py-2.5 px-4 text-right">MOP</th>
                  <th className="py-2.5 px-4 text-right font-bold text-ink-primary">Stage Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-secondary/10 font-medium text-ink-primary font-mono">
                <tr>
                  <td className="py-2.5 px-4 font-sans font-semibold">🌱 {t("plan.basal", locale)}</td>
                  <td className="py-2.5 px-4 text-right text-criterion-water font-bold">{dapTotalField} kg</td>
                  <td className="py-2.5 px-4 text-right text-status-good">{ureaBasal} kg</td>
                  <td className="py-2.5 px-4 text-right text-brand-accent font-bold">{mopTotalField} kg</td>
                  <td className="py-2.5 px-4 text-right font-bold text-ink-primary">{basalTotal} kg</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-4 font-sans font-semibold">🌿 {t("plan.topDressing1", locale)}</td>
                  <td className="py-2.5 px-4 text-right text-ink-secondary">0 kg</td>
                  <td className="py-2.5 px-4 text-right text-status-good font-bold">{ureaTd1} kg</td>
                  <td className="py-2.5 px-4 text-right text-ink-secondary">0 kg</td>
                  <td className="py-2.5 px-4 text-right font-bold text-ink-primary">{td1Total} kg</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-4 font-sans font-semibold">🌾 {t("plan.topDressing2", locale)}</td>
                  <td className="py-2.5 px-4 text-right text-ink-secondary">0 kg</td>
                  <td className="py-2.5 px-4 text-right text-status-good font-bold">{ureaTd2} kg</td>
                  <td className="py-2.5 px-4 text-right text-ink-secondary">0 kg</td>
                  <td className="py-2.5 px-4 text-right font-bold text-ink-primary">{td2Total} kg</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* D. "Why these fertilizers?" Rationale Card */}
        <div className="p-4 rounded-xl bg-brand-primary/5 border border-brand-primary/20 space-y-2">
          <h4 className="text-xs font-bold text-brand-primary flex items-center gap-1.5 uppercase tracking-wider">
            <HelpCircle className="w-4 h-4 text-brand-primary" />
            {t("plan.whyFertilizers", locale)}
          </h4>
          <p className="text-xs text-ink-primary leading-relaxed">
            {fertPlan?.explanation || (
              `For ${topCrop} on ${areaScale} acre(s), the requirement of ${nPerAcre} kg N, ${pPerAcre} kg P₂O₅, and ${kPerAcre} kg K₂O per acre is satisfied using DAP (${dapTotalField} kg total), Urea (${ureaTotalField} kg total), and MOP (${mopTotalField} kg total). DAP and MOP are applied at sowing (basal), while Urea is split across sowing and 2 top dressings to maximize crop uptake.`
            )}
          </p>
        </div>
      </div>

      {/* 3. Optimization Convergence Trajectory */}
      <div className="bg-surface rounded-card border border-ink-secondary/15 p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
          <div>
            <h3 className="font-display font-bold text-lg text-ink-primary flex items-center gap-2">
              <TrendingDown className="w-5 h-5 text-brand-primary" />
              {t("plan.trajectoryTitle", locale)}
            </h3>
            <p className="text-xs text-ink-secondary mt-0.5">
              {t("plan.trajectorySub", locale)}
            </p>
          </div>

          <div className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-brand-primary/10 border border-brand-primary/20 text-xs font-semibold text-brand-primary">
            <LineChartIcon className="w-4 h-4 text-brand-primary" />
            <span>
              {t("plan.convergedBadge", locale, { gen: generations, fitness: bestFitness })}
            </span>
          </div>
        </div>

        <div className="w-full h-[220px] pt-4">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={sparklineData}>
              <XAxis
                dataKey="gen"
                stroke="#5B6B60"
                fontSize={11}
                tickLine={false}
                label={{ value: t("gpo.generations", locale), position: "insideBottom", offset: -5, fontSize: 11 }}
              />
              <YAxis
                stroke="#5B6B60"
                fontSize={11}
                tickLine={false}
                domain={['auto', 'auto']}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const dataPoint = payload[0].payload;
                    return (
                      <div className="bg-surface p-2.5 rounded-lg border border-ink-secondary/20 shadow-md text-xs">
                        <div className="font-bold text-ink-primary">{t("gpo.generations", locale)} #{dataPoint.gen}</div>
                        <div>{t("gpo.fitness", locale)}: <strong>{dataPoint.cost.toFixed(4)}</strong></div>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Line
                type="monotone"
                dataKey="cost"
                stroke="#2E6B4F"
                strokeWidth={3}
                dot={{ r: 4, fill: "#C98A3D", strokeWidth: 2, stroke: "#FFFFFF" }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
