import React from "react";
import MetricCard from "./MetricCard";
import {
  Thermometer,
  CloudRain,
  Droplets,
  TestTube,
  Flame,
  Leaf,
  Layers,
  Activity,
  Eye,
  MapPin,
} from "lucide-react";
import { MapContainer, TileLayer, Marker } from "react-leaflet";
import L from "leaflet";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";
import { t } from "../../i18n";

const customIcon = L.icon({
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

export default function LiveFieldDataPanel({ data, locale }) {
  if (!data) return null;

  const topRef = data.top_crop_reference_ranges || {};
  const p = data.provenance || {};

  const tempRef = topRef.temperature_c;
  const rainRef = topRef.rainfall_mm_last_30d;
  const phRef = topRef.soil_ph;

  return (
    <div className="space-y-8">
      {/* 1. Environmental & Weather Section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-display font-bold text-lg text-ink-primary flex items-center gap-2">
            <Thermometer className="w-5 h-5 text-brand-primary" />
            {t("weather.title", locale)}
          </h3>
          <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-surface border border-ink-secondary/15 text-ink-secondary">
            {t("weather.source", locale, { source: p.weather_source || "Open-Meteo API" })}
          </span>
        </div>

        {/* 4-column grid on desktop */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard
            icon={<Thermometer />}
            label={t("weather.temperature", locale)}
            value={data.avg_temp_c}
            unit="°C"
            rangeMin={tempRef?.min}
            rangeMax={tempRef?.max}
            liveBadge={p.weather_source}
            subtext={t("weather.tempSubtext", locale)}
            locale={locale}
          />

          <MetricCard
            icon={<CloudRain />}
            label={t("weather.rainfall", locale)}
            value={data.rainfall_mm_last_30d}
            unit="mm"
            rangeMin={rainRef?.min}
            rangeMax={rainRef?.max}
            liveBadge={p.weather_source}
            subtext={t("weather.rainSubtext", locale)}
            locale={locale}
          />

          <MetricCard
            icon={<Droplets />}
            label={t("weather.humidity", locale)}
            value={data.humidity_pct}
            unit="%"
            liveBadge={p.weather_source}
            subtext={t("weather.humiditySubtext", locale)}
            locale={locale}
          />

          <MetricCard
            icon={<Flame />}
            label={t("weather.solarRadiation", locale)}
            value={data.solar_radiation_mj_m2}
            unit="MJ/m²"
            liveBadge={p.weather_source}
            subtext={t("weather.solarSubtext", locale)}
            locale={locale}
          />
        </div>
      </div>

      {/* 2. Soil Nutrients & Moisture Section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-display font-bold text-lg text-ink-primary flex items-center gap-2">
            <TestTube className="w-5 h-5 text-criterion-soil" />
            {t("soil.title", locale)}
          </h3>
          <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-surface border border-ink-secondary/15 text-ink-secondary">
            {t("soil.source", locale, {
              source: p.soil_source === "unavailable"
                ? t("status.unavailable", locale)
                : (p.soil_source || "ISRIC SoilGrids")
            })}
          </span>
        </div>

        {/* 4-column grid on desktop */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard
            icon={<TestTube />}
            label={t("soil.ph", locale)}
            value={data.soil_ph}
            unit=""
            rangeMin={phRef?.min}
            rangeMax={phRef?.max}
            liveBadge={p.soil_source}
            subtext={t("soil.phSubtext", locale)}
            locale={locale}
          />

          <MetricCard
            icon={<Leaf />}
            label={t("soil.nitrogen", locale)}
            value={data.soil_nitrogen_mg_kg}
            unit="mg/kg"
            liveBadge={p.soil_source}
            subtext={t("soil.nitrogenSubtext", locale)}
            locale={locale}
          />

          <MetricCard
            icon={<Layers />}
            label={t("soil.organicCarbon", locale)}
            value={data.soil_organic_carbon_g_kg}
            unit="g/kg"
            liveBadge={p.soil_source}
            subtext={t("soil.carbonSubtext", locale)}
            locale={locale}
          />

          <MetricCard
            icon={<Droplets />}
            label={t("soil.soilMoisture", locale)}
            value={data.soil_moisture_pct}
            unit="%"
            liveBadge={p.soil_source}
            subtext={t("soil.moistureSubtext", locale)}
            locale={locale}
          />
        </div>
      </div>

      {/* 3. Satellite Vegetation & High-Res Sentinel View */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-display font-bold text-lg text-ink-primary flex items-center gap-2">
            <Eye className="w-5 h-5 text-criterion-water" />
            {t("satellite.title", locale)}
          </h3>
          <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-surface border border-ink-secondary/15 text-ink-secondary">
            {t("satellite.source", locale, { source: p.satellite_source || "Copernicus Sentinel-2" })}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-stretch">
          {/* Left: NDVI Metric Highlight */}
          <div className="md:col-span-5 flex flex-col">
            <div className="bg-surface rounded-card border border-ink-secondary/15 p-6 shadow-sm flex-1 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold tracking-wider uppercase text-ink-secondary">
                    {t("satellite.ndviLabel", locale)}
                  </span>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-brand-primary/10 text-brand-primary uppercase">
                    {t("satellite.bandLabel", locale)}
                  </span>
                </div>

                <div className="mt-4 flex items-baseline gap-3">
                  <span className="font-display font-bold text-4xl text-ink-primary">
                    {data.ndvi !== null && data.ndvi !== undefined ? data.ndvi : t("status.naBadge", locale)}
                  </span>
                  <span className="text-xs font-medium text-status-good bg-status-good/10 px-2 py-0.5 rounded">
                    {t("satellite.healthyBiomass", locale)}
                  </span>
                </div>

                <p className="text-xs text-ink-secondary mt-3 leading-relaxed">
                  {t("satellite.ndviDesc", locale)}
                </p>
              </div>

              {data.satellite_scene_date && (
                <div className="mt-6 pt-4 border-t border-ink-secondary/15 flex items-center justify-between text-xs text-ink-secondary">
                  <span>{t("satellite.sceneDate", locale, { date: new Date(data.satellite_scene_date).toLocaleDateString() })}</span>
                </div>
              )}
            </div>
          </div>

          {/* Right: Clean Sentinel-2 Satellite Tile Viewer */}
          <div className="md:col-span-7">
            <div className="bg-surface rounded-card border border-ink-secondary/15 shadow-sm overflow-hidden flex flex-col h-full">
              <div className="px-4 py-3 bg-base border-b border-ink-secondary/15 flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-ink-secondary flex items-center gap-1.5">
                  <Activity className="w-4 h-4 text-brand-primary" />
                  {t("satellite.liveView", locale)}
                </span>
                <span className="text-[10px] font-bold text-ink-secondary bg-surface px-2 py-0.5 rounded border border-ink-secondary/15">
                  {t("satellite.resolution", locale)}
                </span>
              </div>

              {/* Leaflet Satellite Map Layer */}
              <div className="relative w-full h-[230px] bg-ink-primary">
                {data.location ? (
                  <MapContainer
                    center={[data.location.lat, data.location.lon]}
                    zoom={14}
                    style={{ height: "100%", width: "100%" }}
                    zoomControl={false}
                    attributionControl={false}
                  >
                    <TileLayer
                      url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                      maxZoom={18}
                    />
                    <Marker
                      position={[data.location.lat, data.location.lon]}
                      icon={customIcon}
                    />
                  </MapContainer>
                ) : (
                  <div className="flex items-center justify-center h-full text-xs text-surface/70">
                    {t("satellite.noLocation", locale)}
                  </div>
                )}


                {/* Bottom Overlay Label */}
                {data.location && (
                  <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-ink-primary/90 to-transparent p-3 text-surface text-[11px] flex items-center justify-between z-[400]">
                    <div className="flex items-center gap-1">
                      <MapPin className="w-3.5 h-3.5 text-brand-accent" />
                      <span>
                        {t("satellite.centroid", locale, { lat: data.location.lat.toFixed(4), lon: data.location.lon.toFixed(4) })}
                      </span>
                    </div>
                    <span className="text-[10px] text-surface/80">Esri / Copernicus Sentinel-2</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
