import { getTemperatureStatus, getRainfallStatus, getHumidityStatus, getSoilPhStatus, getNitrogenStatus, getOrganicCarbonStatus, getSoilMoistureStatus, getNdviStatus, statusToEmoji, buildExplanation, buildIrrigationSchedule } from "../utils/statusHelpers";
import { getCurrentLocale, t, translateCropName } from "../i18n";

function StatCard({ label, value, unit, badge, isUnavailable, interpretation }) {
  const displayValue = isUnavailable ? "—" : value;
  return (
    <div className="rounded-lg border bg-white px-4 py-3" style={{ borderColor: "var(--line)" }}>
      <div className="flex items-center justify-between">
        <div className="text-xs uppercase tracking-wide" style={{ color: "var(--soil-600)" }}>{label}</div>
        {badge && <SourceBadge source={badge} />}
      </div>
      <div className="text-2xl font-semibold mt-1" style={{ color: isUnavailable ? "var(--soil-600)" : "var(--leaf-700)" }}>
        {displayValue} <span className="text-sm font-normal" style={{ color: "var(--soil-600)" }}>{unit}</span>
      </div>
      {interpretation && (
        <div className="mt-2 text-sm" style={{ color: "var(--soil-600)" }}>
          <div>{statusToEmoji(interpretation.status)} {interpretation.farmerFriendly || interpretation.label}</div>
          <div className="text-xs mt-1">{interpretation.why || interpretation.explanation || interpretation.label}</div>
        </div>
      )}
    </div>
  );
}

function SourceBadge({ source }) {
  const locale = getCurrentLocale();
  let badgeText = t("status.live", locale);
  let bgColor = "var(--leaf-100)";
  let textColor = "var(--leaf-700)";
  let tooltip = `${t("status.live", locale)}: ${source}`;
  
  if (source === "mock") {
    badgeText = t("status.mock", locale);
    bgColor = "#f3e6d8";
    textColor = "var(--clay)";
    tooltip = t("status.mockFallback", locale);
  } else if (source === "unavailable") {
    badgeText = t("status.unavailable", locale);
    bgColor = "#fee2e2";
    textColor = "#991b1b";
    tooltip = t("status.serviceUnavailable", locale);
  }
  
  return (
    <span
      className="text-[10px] px-1.5 py-0.5 rounded font-medium"
      style={{ background: bgColor, color: textColor }}
      title={tooltip}
    >
      {badgeText}
    </span>
  );
}

function WeightBar({ label, value, locale }) {
  const key = `mcdm.${label}`;
  const translated = t(key, locale);
  const translatedLabel = (translated && translated !== key)
    ? translated
    : (t(`mcdm.criteria_${label}`, locale) !== `mcdm.criteria_${label}`
        ? t(`mcdm.criteria_${label}`, locale)
        : label.replace(/_/g, " "));
  return (
    <div>
      <div className="flex justify-between text-xs mb-1" style={{ color: "var(--soil-600)" }}>
        <span>{translatedLabel}</span>
        <span>{(value * 100).toFixed(1)}%</span>
      </div>
      <div className="h-1.5 rounded-full bg-black/5">
        <div className="h-1.5 rounded-full" style={{ width: `${value * 100}%`, background: "var(--leaf-600)" }} />
      </div>
    </div>
  );
}


export default function ResultsPanel({ data, loading, error }) {
  const locale = getCurrentLocale();

  if (loading) {
    return <div className="text-sm" style={{ color: "var(--soil-600)" }}>{t("common.loading", locale)}</div>;
  }
  if (error) {
    return <div className="text-sm text-red-700">{error}</div>;
  }
  if (!data) {
    return (
      <div className="text-sm" style={{ color: "var(--soil-600)" }}>
        {t("dashboard.emptyState", locale)}
      </div>
    );
  }

  const top = data.crop_ranking[0];
  const translatedTopCrop = translateCropName(top.crop, locale);
  const p = data.provenance;
  const topRef = data.top_crop_reference_ranges || {};

  const tempInterp = getTemperatureStatus(data.avg_temp_c, topRef.temperature_c, top.crop, locale);
  const rainInterp = getRainfallStatus(data.rainfall_mm_last_30d, topRef.rainfall_mm_last_30d, top.crop, locale);
  const humInterp = getHumidityStatus(data.humidity_pct, topRef.humidity_pct, top.crop, locale);
  const phInterp = getSoilPhStatus(data.soil_ph, topRef.soil_ph, top.crop, locale);
  const nInterp = getNitrogenStatus(data.soil_nitrogen_mg_kg, topRef.nitrogen_mg_kg, top.crop, locale);
  const ocInterp = getOrganicCarbonStatus(data.soil_organic_carbon_g_kg, topRef.organic_carbon_g_kg, top.crop, locale);
  const smInterp = getSoilMoistureStatus(data.soil_moisture_pct, topRef.soil_moisture_pct, top.crop, locale);
  const ndviInterp = p.satellite_source === "unavailable" ? getNdviStatus(null, locale) : getNdviStatus(data.ndvi, locale);

  const rankingWhy = t("dashboard.rankingWhy", locale, {
    crop: translatedTopCrop,
    score: top.topsis_closeness,
  });

  return (
    <div className="space-y-6">
      <div>
        <div className="rounded-lg border px-4 py-4 bg-white" style={{ borderColor: "var(--line)" }}>
          <div className="text-sm font-display uppercase tracking-wide text-[var(--leaf-700)]">🌾 {t("recommendation.topCropInRun", locale)}</div>
          <div className="mt-3 flex items-center justify-between gap-4">
            <div>
              <div className="text-2xl font-bold">{translatedTopCrop}</div>
              <div className="text-sm mt-1 text-[var(--soil-600)]">{t("dashboard.topsis", locale)}: {top.topsis_closeness} · {t("dashboard.electre", locale)}: {top.electre_net_outranking > 0 ? "+" : ""}{top.electre_net_outranking}</div>
            </div>
            <div className="text-sm text-right" style={{ color: "var(--soil-600)" }}>
              <div><strong>{t("recommendation.why", locale)}</strong></div>
              <div className="mt-1">{rankingWhy}</div>
            </div>
          </div>
        </div>

        <div className="rounded-lg border mt-4 px-4 py-4 bg-white" style={{ borderColor: "var(--line)" }}>
          <div className="text-sm font-display uppercase tracking-wide text-[var(--leaf-700)]">👨‍🌾 {t("recommendation.whatThisMeans", locale)}</div>
          <div className="mt-3 text-sm">
            <div><strong>{t("recommendation.currentTopCrop", locale)}:</strong> {translatedTopCrop}</div>
            <div><strong>{t("recommendation.referenceComparison", locale)}:</strong> {t("recommendation.referenceComparisonText", locale, { crop: translatedTopCrop })}</div>
            <div><strong>{t("recommendation.waterPlan", locale)}:</strong> ~{Math.round(data.resource_plan.water_liters_per_week / 7).toLocaleString()} L/day</div>
            <div><strong>{t("recommendation.fertilizerPlan", locale)}:</strong> ~{data.resource_plan.fertilizer_kg_per_acre} kg/acre</div>
            <div><strong>{t("recommendation.irrigationSchedule", locale)}:</strong> {buildIrrigationSchedule(data.resource_plan, locale)}</div>
            <div className="mt-2"><strong>{t("recommendation.interpretation", locale)}:</strong> {tempInterp.why}</div>
          </div>
        </div>
      </div>

      {/* TECHNICAL ANALYSIS: Weather, Soil, Satellite, AHP, Ranking, GPO */}
      {/* Weather Data Section */}
      <div>
        <h3 className="text-sm font-display mb-2 uppercase tracking-wide" style={{ color: "var(--leaf-700)" }}>
          {t("weather.title", locale)} ({t("weather.source", locale)})
        </h3>
        <div className="grid grid-cols-3 gap-2">
          <StatCard label={t("weather.temperature", locale)} value={data.avg_temp_c} unit="°C" badge={p.weather_source} isUnavailable={p.weather_source === "unavailable"} interpretation={tempInterp} />
          <StatCard label={t("weather.rainfall", locale)} value={data.rainfall_mm_last_30d} unit="mm" badge={p.weather_source} isUnavailable={p.weather_source === "unavailable"} interpretation={rainInterp} />
          <StatCard label={t("weather.humidity", locale)} value={data.humidity_pct} unit="%" badge={p.weather_source} isUnavailable={p.weather_source === "unavailable"} interpretation={humInterp} />
        </div>
      </div>

      {/* Soil Data Section */}
      <div>
        <h3 className="text-sm font-display mb-2 uppercase tracking-wide" style={{ color: "var(--leaf-700)" }}>
          {t("soil.title", locale)} ({t("soil.source", locale)})
        </h3>
        <div className="grid grid-cols-3 gap-2">
          <StatCard label={t("soil.ph", locale)} value={data.soil_ph} unit="" badge={p.soil_source} isUnavailable={p.soil_source === "unavailable"} interpretation={phInterp} />
          <StatCard label={t("soil.nitrogen", locale)} value={data.soil_nitrogen_mg_kg} unit="mg/kg" badge={p.soil_source} isUnavailable={p.soil_source === "unavailable"} interpretation={nInterp} />
          <StatCard label={t("soil.organicCarbon", locale)} value={data.soil_organic_carbon_g_kg} unit="g/kg" badge={p.soil_source} isUnavailable={p.soil_source === "unavailable"} interpretation={ocInterp} />
        </div>
        <div className="mt-2">
          <StatCard label={t("soil.soilMoisture", locale)} value={data.soil_moisture_pct} unit="%" badge={p.soil_source} isUnavailable={p.soil_source === "unavailable"} interpretation={smInterp} />
        </div>
      </div>

      {/* Satellite/NDVI Section */}
      <div>
        <h3 className="text-sm font-display mb-2 uppercase tracking-wide" style={{ color: "var(--leaf-700)" }}>
          {t("vegetation.title", locale)} ({t("vegetation.source", locale)} NDVI)
        </h3>
        <div className="rounded-lg border bg-white px-4 py-3" style={{ borderColor: "var(--line)" }}>
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <div className="text-xs uppercase tracking-wide" style={{ color: "var(--soil-600)" }}>{t("vegetation.ndviIndex", locale)}</div>
              {p.satellite_source === "unavailable" ? (
                <div className="text-3xl font-semibold mt-1" style={{ color: "var(--soil-600)" }}>
                  {t("vegetation.ndviUnavailable", locale)}
                  <div className="text-sm font-normal mt-1" style={{ color: "var(--soil-600)" }}>{ndviInterp.label}</div>
                  <div className="text-xs mt-1" style={{ color: "var(--soil-600)" }}>{ndviInterp.why}</div>
                </div>
              ) : (
                <div className="text-3xl font-semibold mt-1" style={{ color: "var(--leaf-700)" }}>
                  {data.ndvi} <div className="text-sm font-normal mt-1" style={{ color: "var(--soil-600)" }}>{statusToEmoji(ndviInterp.status)} {ndviInterp.farmerFriendly || ndviInterp.label}</div>
                </div>
              )}
              <div className="text-xs mt-1" style={{ color: "var(--soil-600)" }}>
                {t("status.ndviFormula", locale)}
              </div>
              {data.satellite_scene_date && p.satellite_source !== "unavailable" && (
                <div className="text-xs mt-2" style={{ color: "var(--soil-600)" }}>
                  {t("vegetation.sceneDate", locale)}: <strong>{new Date(data.satellite_scene_date).toLocaleDateString()}</strong>
                </div>
              )}
            </div>
            <SourceBadge source={p.satellite_source} />
          </div>
        </div>

        {/* Sentinel-2 Satellite Image Viewer */}
        {data.satellite_tile_url && p.satellite_source !== "unavailable" && (
          <div className="mt-4 rounded-lg border bg-white overflow-hidden" style={{ borderColor: "var(--line)" }}>
            <div className="text-xs uppercase tracking-wide p-3 pb-2" style={{ color: "var(--soil-600)" }}>{t("vegetation.liveSatelliteView", locale)}</div>
            <div className="w-full h-56 bg-gray-200 relative">
              <iframe
                src={`https://maps.sentinel-hub.com/?zoom=13&lat=${data.location.lat}&lng=${data.location.lon}&view=true-color&showCoverage=true`}
                width="100%"
                height="100%"
                style={{ border: "none" }}
                loading="lazy"
                title="Sentinel-2 Satellite View"
              />
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent text-white text-[11px] px-3 py-2">
                <div>{t("common.latitude", locale)}: {data.location.lat.toFixed(4)}, {t("common.longitude", locale)}: {data.location.lon.toFixed(4)}</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* AHP Weights Section */}
      <div>
        <h3 className="text-sm font-display mb-2 uppercase tracking-wide" style={{ color: "var(--leaf-700)" }}>
          {t("mcdm.title", locale)}
          <span
            className="ml-2 text-[10px] align-middle px-1.5 py-0.5 rounded font-medium"
            style={{ background: data.ahp_is_consistent ? "var(--leaf-100)" : "#fde2e2", color: data.ahp_is_consistent ? "var(--leaf-700)" : "#b91c1c" }}
          >
            {t("mcdm.consistencyRatio", locale)} = {data.ahp_consistency_ratio} {data.ahp_is_consistent ? "✓" : "⚠"}
          </span>
        </h3>
        <div className="rounded-lg border bg-white px-4 py-3 space-y-2" style={{ borderColor: "var(--line)" }}>
          {Object.entries(data.ahp_weights).map(([k, v]) => <WeightBar key={k} label={k} value={v} locale={locale} />)}
        </div>
      </div>

      {/* Crop Ranking Section */}
      <div>
        <h3 className="text-sm font-display mb-2 uppercase tracking-wide" style={{ color: "var(--leaf-700)" }}>
          {t("dashboard.ranking", locale)} ({t("dashboard.topsis", locale)} + {t("dashboard.electre", locale)})
        </h3>
        <div className="space-y-2">
          {data.crop_ranking.map((c) => (
            <div
              key={c.crop}
              className="flex items-center justify-between rounded-lg border px-4 py-3"
              style={{
                borderColor: c.rank === 1 ? "var(--leaf-600)" : "var(--line)",
                background: c.rank === 1 ? "var(--leaf-100)" : "white",
              }}
            >
              <div className="font-medium">{c.rank}. {translateCropName(c.crop, locale)}</div>
              <div className="flex gap-4 text-xs" style={{ color: "var(--soil-600)" }}>
                <span>{t("dashboard.topsis", locale)}: <strong style={{ color: "var(--leaf-700)" }}>{c.topsis_closeness}</strong></span>
                <span>{t("dashboard.electre", locale)}: <strong style={{ color: "var(--leaf-700)" }}>{c.electre_net_outranking > 0 ? "+" : ""}{c.electre_net_outranking}</strong></span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Resource Plan Section */}
      <div>
        <h3 className="text-sm font-display mb-2 uppercase tracking-wide" style={{ color: "var(--leaf-700)" }}>
          {t("gpo.title", locale)} {t("recommendation.for", locale)} {translatedTopCrop}
        </h3>
        <div className="rounded-lg border px-4 py-3 bg-white" style={{ borderColor: "var(--line)" }}>
          <div className="grid grid-cols-2 gap-3 text-sm mb-3">
            <div><span style={{ color: "var(--soil-600)" }}>{t("gpo.water", locale)}:</span> <strong>{data.resource_plan.water_liters_per_week.toLocaleString()}</strong> {t("gpo.waterUnit", locale)}</div>
            <div><span style={{ color: "var(--soil-600)" }}>{t("gpo.fertilizer", locale)}:</span> <strong>{data.resource_plan.fertilizer_kg_per_acre}</strong> {t("gpo.fertilizerUnit", locale)}</div>
          </div>
          <div className="text-sm mb-2"><span style={{ color: "var(--soil-600)" }}>{t("gpo.schedule", locale)}:</span> {buildIrrigationSchedule(data.resource_plan, locale)}</div>
          <div className="text-xs" style={{ color: "var(--soil-600)" }}>
            {t("gpo.converged", locale)}: {data.resource_plan.optimizer_generations_run} {t("gpo.generations", locale)} · {t("gpo.fitness", locale)}: {data.resource_plan.optimizer_best_fitness}
          </div>
        </div>
      </div>

      <div className="rounded-lg border-l-4 px-4 py-3 text-sm" style={{ borderColor: "var(--clay)", background: "#fbf3ec" }}>
        <strong>{t("recommendation.explanationTitle", locale)}:</strong>
        <div className="mt-2">{buildExplanation(data, locale)}</div>
      </div>

      {/* Data Source Footer */}
      <div className="text-[10px]" style={{ color: "var(--soil-600)", paddingTop: "8px", borderTop: "1px solid var(--line)" }}>
        <strong>{t("recommendation.sourceFooter", locale)}:</strong> {t("vegetation.source", locale)}: {p.satellite_source} · {t("weather.source", locale)}: {p.weather_source} · {t("soil.source", locale)}: {p.soil_source} · {t("common.market", locale)}: {p.market_source}
      </div>
    </div>
  );
}

