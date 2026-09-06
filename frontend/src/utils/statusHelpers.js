import { getCurrentLocale, t, translateCropName } from "../i18n";

function buildRangeInterpretation({ label, value, unit, reference, cropName, metricName, locale = getCurrentLocale() }) {
  const translatedCrop = translateCropName(cropName, locale);

  if (value === null || value === undefined) {
    return {
      status: "unavailable",
      label: `${label} ${t("status.unavailable", locale)}`,
      technical: `${label}: ${t("status.unavailable", locale)}`,
      farmerFriendly: `⚪ ${t("status.comparisonUnavailable", locale)}`,
      why: t("status.referenceUnavailable", locale),
    };
  }

  const numberValue = Number(value);
  if (Number.isNaN(numberValue) || !reference || reference.min === undefined || reference.max === undefined) {
    return {
      status: "unavailable",
      label: `${label} ${t("status.referenceUnavailable", locale)}`,
      technical: `${label}: ${value}${unit ? ` ${unit}` : ""}`,
      farmerFriendly: `⚪ ${t("status.comparisonUnavailable", locale)}`,
      why: t("status.referenceUnavailable", locale),
    };
  }

  const lowerBound = Number(reference.min);
  const upperBound = Number(reference.max);
  const withinRange = numberValue >= lowerBound && numberValue <= upperBound;
  const rangeText = t("status.rangeLabel", locale, {
    min: lowerBound,
    max: upperBound,
    unit: unit || "",
  });

  if (withinRange) {
    return {
      status: "within_reference",
      label: `${label} ${t("status.withinRangeLabel", locale)}`,
      technical: `${label}: ${numberValue}${unit ? ` ${unit}` : ""}`,
      farmerFriendly: `🟢 ${t("status.withinReference", locale, { crop: translatedCrop, metric: label })}`,
      why: rangeText,
    };
  }

  const trendKey = numberValue < lowerBound ? "status.belowReference" : "status.aboveReference";
  const trendText = t(trendKey, locale, {
    crop: translatedCrop,
    metric: label,
  });

  return {
    status: "outside_reference",
    label: `${label} ${t("status.outsideRangeLabel", locale)}`,
    technical: `${label}: ${numberValue}${unit ? ` ${unit}` : ""}`,
    farmerFriendly: `🔴 ${trendText}`,
    why: rangeText,
  };
}

export function getTemperatureStatus(value, reference = null, cropName = "crop", locale = getCurrentLocale()) {
  return buildRangeInterpretation({
    label: t("dashboard.temperature", locale),
    value,
    unit: "°C",
    reference,
    cropName,
    metricName: "temperature",
    locale,
  });
}

export function getRainfallStatus(value, reference = null, cropName = "crop", locale = getCurrentLocale()) {
  return buildRangeInterpretation({
    label: t("dashboard.rainfall", locale),
    value,
    unit: "mm",
    reference,
    cropName,
    metricName: "rainfall",
    locale,
  });
}

export function getHumidityStatus(value, reference = null, cropName = "crop", locale = getCurrentLocale()) {
  return buildRangeInterpretation({
    label: t("dashboard.humidity", locale),
    value,
    unit: "%",
    reference,
    cropName,
    metricName: "humidity",
    locale,
  });
}

export function getSoilPhStatus(value, reference = null, cropName = "crop", locale = getCurrentLocale()) {
  return buildRangeInterpretation({
    label: t("soil.ph", locale),
    value,
    unit: "",
    reference,
    cropName,
    metricName: "soil pH",
    locale,
  });
}

export function getNitrogenStatus(value, reference = null, cropName = "crop", locale = getCurrentLocale()) {
  return buildRangeInterpretation({
    label: t("soil.nitrogen", locale),
    value,
    unit: "mg/kg",
    reference,
    cropName,
    metricName: "soil nitrogen",
    locale,
  });
}

export function getOrganicCarbonStatus(value, reference = null, cropName = "crop", locale = getCurrentLocale()) {
  return buildRangeInterpretation({
    label: t("soil.organicCarbon", locale),
    value,
    unit: "g/kg",
    reference,
    cropName,
    metricName: "soil organic carbon",
    locale,
  });
}

export function getSoilMoistureStatus(value, reference = null, cropName = "crop", locale = getCurrentLocale()) {
  return buildRangeInterpretation({
    label: t("soil.soilMoisture", locale),
    value,
    unit: "%",
    reference,
    cropName,
    metricName: "soil moisture",
    locale,
  });
}

export function getNdviStatus(value, locale = getCurrentLocale()) {
  if (value === null || value === undefined) {
    return {
      status: "unavailable",
      label: t("dashboard.ndviUnavailable", locale),
      technical: `NDVI: ${t("status.unavailable", locale)}`,
      farmerFriendly: `🟠 ${t("status.ndviUnavailable", locale)}`,
      why: t("status.ndviShort", locale),
    };
  }

  const numberValue = Number(value);
  if (Number.isNaN(numberValue)) {
    return {
      status: "unavailable",
      label: t("dashboard.ndviUnavailable", locale),
      technical: `NDVI: ${value}`,
      farmerFriendly: `⚪ ${t("status.comparisonUnavailable", locale)}`,
      why: t("status.ndviNotNumeric", locale),
    };
  }

  return {
    status: "observed_value",
    label: t("dashboard.ndviIndex", locale),
    technical: `NDVI: ${numberValue}`,
    farmerFriendly: `📌 ${t("status.ndviObserved", locale, { value: numberValue })}`,
    why: t("status.ndviObservedText", locale, { value: numberValue }),
  };
}

export function statusToEmoji(status) {
  if (status === "within_reference") return "✅";
  if (status === "outside_reference") return "⚠️";
  if (status === "unavailable") return "⚪";
  return "📌";
}

/**
 * Build translated AI explanation from recommendation data
 * Reconstructs the explanation with proper translations for each language
 */
export function buildExplanation(data, locale = getCurrentLocale()) {
  if (!data || !data.crop_ranking || data.crop_ranking.length === 0) {
    return t("recommendation.finalRecommendation", locale);
  }

  const topCrop = data.crop_ranking[0].crop;
  const translatedTopCrop = translateCropName(topCrop, locale);
  const topsisScore = data.crop_ranking[0].topsis_closeness;
  
  // Find dominant criterion from AHP weights
  const dominantCriterion = Object.entries(data.ahp_weights || {}).reduce(
    ([maxKey, maxVal], [key, val]) => val > maxVal ? [key, val] : [maxKey, maxVal],
    ["climate_suitability", 0]
  )[0];
  
  const ahpWeight = data.ahp_weights?.[dominantCriterion] || 0;
  const criterionKey = `mcdm.${dominantCriterion}`;
  const translatedCriterion = t(criterionKey, locale);
  const criterionLabel = (translatedCriterion && translatedCriterion !== criterionKey)
    ? translatedCriterion
    : (t(`mcdm.criteria_${dominantCriterion}`, locale) !== `mcdm.criteria_${dominantCriterion}`
        ? t(`mcdm.criteria_${dominantCriterion}`, locale)
        : dominantCriterion.replace(/_/g, " "));

  
  const resourcePlan = data.resource_plan || {};
  
  return t("recommendation.aiExplanation", locale, {
    crop: translatedTopCrop,
    topsis: topsisScore.toFixed(3),
    criterion: criterionLabel,
    weight: ahpWeight.toFixed(2),
    water: resourcePlan.water_liters_per_week?.toFixed(0) || "0",
    fertilizer: resourcePlan.fertilizer_kg_per_acre?.toFixed(1) || "0",
    fitness: resourcePlan.optimizer_best_fitness?.toFixed(4) || "0",
    generations: resourcePlan.optimizer_generations_run || "0",
  });
}

/**
 * Build translated irrigation schedule from resource plan
 * Reconstructs the schedule text with proper translations for each language
 */
export function buildIrrigationSchedule(resourcePlan, locale = getCurrentLocale()) {
  if (!resourcePlan || !resourcePlan.water_liters_per_week) {
    return t("status.unavailable", locale);
  }

  const waterPerDay = (resourcePlan.water_liters_per_week / 7).toFixed(0);
  
  return t("recommendation.irrigationScheduleValue", locale, {
    water: Number(waterPerDay).toLocaleString(),
    waterings: "2-3",
  });
}


