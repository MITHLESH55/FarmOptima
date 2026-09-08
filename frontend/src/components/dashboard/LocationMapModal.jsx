import React, { useState, useEffect } from "react";
import { MapContainer, TileLayer, Marker, useMapEvents, useMap } from "react-leaflet";
import L from "leaflet";
import { X, Check, MapPin, Map, Navigation, CheckCircle2, AlertCircle } from "lucide-react";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";
import { t } from "../../i18n";
import { validateCoordinates, formatCoordinates } from "../../utils/locationValidation";

const customIcon = L.icon({
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

function ClickCapture({ onSelect }) {
  useMapEvents({
    click(e) {
      onSelect({ lat: e.latlng.lat, lon: e.latlng.lng });
    },
  });
  return null;
}

function RecenterMap({ position }) {
  const map = useMap();
  useEffect(() => {
    if (position && typeof position.lat === "number" && typeof position.lon === "number") {
      map.setView([position.lat, position.lon], Math.max(map.getZoom() || 12, 10));
    }
  }, [position, map]);
  return null;
}

export default function LocationMapModal({ isOpen, onClose, position, onSelect, onConfirm, locale }) {
  const [activeTab, setActiveTab] = useState("map"); // "map" | "manual"
  const [latInput, setLatInput] = useState("");
  const [lonInput, setLonInput] = useState("");
  const [validationResult, setValidationResult] = useState({ isValid: false, errorKey: null, lat: null, lon: null });
  const [validatedBadge, setValidatedBadge] = useState(false);

  // Sync inputs when position prop changes or modal opens
  useEffect(() => {
    if (position && typeof position.lat === "number" && typeof position.lon === "number") {
      setLatInput(position.lat.toString());
      setLonInput(position.lon.toString());
      const res = validateCoordinates(position.lat, position.lon);
      setValidationResult(res);
      setValidatedBadge(res.isValid);
    } else {
      setLatInput("");
      setLonInput("");
      setValidationResult({ isValid: false, errorKey: null, lat: null, lon: null });
      setValidatedBadge(false);
    }
  }, [position, isOpen]);

  if (!isOpen) return null;

  const center = position && typeof position.lat === "number" && typeof position.lon === "number"
    ? [position.lat, position.lon]
    : [20.5937, 78.9629]; // Default India centroid

  const handleValidateManualInput = () => {
    const result = validateCoordinates(latInput, lonInput);
    setValidationResult(result);
    if (result.isValid) {
      setValidatedBadge(true);
      if (onSelect) {
        onSelect({ lat: result.lat, lon: result.lon });
      }
    } else {
      setValidatedBadge(false);
    }
  };

  const handleLatChange = (e) => {
    setLatInput(e.target.value);
    setValidatedBadge(false);
  };

  const handleLonChange = (e) => {
    setLonInput(e.target.value);
    setValidatedBadge(false);
  };

  const handleConfirmLocation = () => {
    if (activeTab === "manual" && !validatedBadge) {
      const result = validateCoordinates(latInput, lonInput);
      if (!result.isValid) {
        setValidationResult(result);
        return;
      }
      onSelect({ lat: result.lat, lon: result.lon });
      if (onConfirm) onConfirm({ lat: result.lat, lon: result.lon });
    } else if (position) {
      if (onConfirm) onConfirm(position);
    }
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink-primary/60 backdrop-blur-sm animate-fadeIn">
      <div className="bg-surface rounded-card shadow-2xl border border-ink-secondary/20 w-full max-w-4xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-ink-secondary/15 bg-base flex items-center justify-between">
          <div>
            <h3 className="font-display font-bold text-lg text-ink-primary flex items-center gap-2">
              <MapPin className="w-5 h-5 text-brand-primary" />
              {t("mapModal.title", locale)}
            </h3>
            <p className="text-xs text-ink-secondary mt-0.5">
              {t("mapModal.subtitle", locale)}
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center text-ink-secondary hover:text-ink-primary hover:bg-ink-secondary/10 transition-colors flex-shrink-0"
            aria-label={t("common.close", locale)}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Prominent Tab Controller Bar */}
        <div className="flex border-b border-ink-secondary/15 bg-base px-6 pt-3 pb-0 gap-2">
          <button
            type="button"
            onClick={() => setActiveTab("map")}
            className={`px-5 py-3 font-bold text-sm border-b-2 flex items-center gap-2 transition-all ${
              activeTab === "map"
                ? "border-brand-primary text-brand-primary bg-surface shadow-xs rounded-t-lg"
                : "border-transparent text-ink-secondary hover:text-ink-primary"
            }`}
          >
            <Map className="w-4 h-4" />
            <span>{t("mapModal.tabMap", locale)}</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("manual")}
            className={`px-5 py-3 font-bold text-sm border-b-2 flex items-center gap-2 transition-all ${
              activeTab === "manual"
                ? "border-brand-primary text-brand-primary bg-surface shadow-xs rounded-t-lg"
                : "border-transparent text-ink-secondary hover:text-ink-primary"
            }`}
          >
            <Navigation className="w-4 h-4" />
            <span>{t("mapModal.tabManual", locale)}</span>
          </button>
        </div>

        {/* Modal Body */}
        {activeTab === "map" ? (
          /* Map View Tab */
          <div className="relative w-full h-[450px] bg-ink-secondary/10">
            <MapContainer
              center={center}
              zoom={position ? 12 : 5}
              style={{ height: "100%", width: "100%" }}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              <ClickCapture
                onSelect={(pos) => {
                  onSelect(pos);
                  setLatInput(pos.lat.toString());
                  setLonInput(pos.lon.toString());
                  setValidatedBadge(true);
                  setValidationResult({ isValid: true, errorKey: null, lat: pos.lat, lon: pos.lng });
                }}
              />
              <RecenterMap position={position} />
              {position && typeof position.lat === "number" && typeof position.lon === "number" && (
                <Marker position={[position.lat, position.lon]} icon={customIcon} />
              )}
            </MapContainer>

            {/* Coordinate overlay badge */}
            {position && typeof position.lat === "number" && typeof position.lon === "number" && (
              <div className="absolute bottom-4 left-4 z-[400] bg-surface/90 backdrop-blur-md px-3.5 py-2 rounded-lg border border-ink-secondary/20 shadow-md text-xs font-semibold text-ink-primary flex items-center gap-2">
                <MapPin className="w-4 h-4 text-brand-accent" />
                <span>
                  {formatCoordinates(position.lat, position.lon)}
                </span>
              </div>
            )}
          </div>
        ) : (
          /* Manual Coordinates Tab */
          <div className="w-full h-[450px] bg-base p-6 overflow-y-auto flex flex-col justify-between">
            <div className="max-w-xl mx-auto w-full space-y-6">
              <div className="bg-surface p-6 rounded-card border border-ink-secondary/20 shadow-sm space-y-5">
                <div>
                  <h4 className="text-base font-bold text-ink-primary flex items-center gap-2">
                    <Navigation className="w-5 h-5 text-brand-primary" />
                    {t("mapModal.tabManual", locale)}
                  </h4>
                  <p className="text-xs text-ink-secondary mt-1">
                    {t("mapModal.helperText", locale)}
                  </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Latitude Field */}
                  <div>
                    <label htmlFor="lat-input" className="block text-xs font-semibold uppercase tracking-wider text-ink-secondary mb-1.5">
                      {t("mapModal.latitudeLabel", locale)} <span className="text-status-risk">*</span>
                    </label>
                    <input
                      id="lat-input"
                      type="text"
                      value={latInput}
                      onChange={handleLatChange}
                      placeholder={t("mapModal.latitudePlaceholder", locale)}
                      className="w-full px-3.5 py-2.5 bg-base border border-ink-secondary/25 rounded-lg text-sm font-mono text-ink-primary focus:outline-none focus:border-brand-primary focus:ring-1 focus:ring-brand-primary transition-all"
                    />
                  </div>

                  {/* Longitude Field */}
                  <div>
                    <label htmlFor="lon-input" className="block text-xs font-semibold uppercase tracking-wider text-ink-secondary mb-1.5">
                      {t("mapModal.longitudeLabel", locale)} <span className="text-status-risk">*</span>
                    </label>
                    <input
                      id="lon-input"
                      type="text"
                      value={lonInput}
                      onChange={handleLonChange}
                      placeholder={t("mapModal.longitudePlaceholder", locale)}
                      className="w-full px-3.5 py-2.5 bg-base border border-ink-secondary/25 rounded-lg text-sm font-mono text-ink-primary focus:outline-none focus:border-brand-primary focus:ring-1 focus:ring-brand-primary transition-all"
                    />
                  </div>
                </div>

                {/* Validation Error Message */}
                {validationResult.errorKey && !validatedBadge && (
                  <div className="flex items-center gap-2 text-xs text-status-risk bg-status-risk/10 p-3 rounded-lg border border-status-risk/20 font-medium animate-fadeIn">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    <span>{t(validationResult.errorKey, locale)}</span>
                  </div>
                )}

                {/* Success Validation Status Badge */}
                {validatedBadge && position && (
                  <div className="p-4 rounded-lg bg-brand-primary/10 border border-brand-primary/20 space-y-3 animate-fadeIn">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-brand-primary" />
                      <div>
                        <span className="block font-bold text-ink-primary text-sm">
                          ✓ {t("mapModal.validCoordinates", locale)}
                        </span>
                        <span className="text-ink-secondary font-mono text-xs">
                          {formatCoordinates(position.lat, position.lon)}
                        </span>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={handleConfirmLocation}
                      className="w-full py-2 px-4 rounded-lg bg-brand-primary text-surface font-semibold text-xs hover:bg-brand-primary/90 transition-colors flex items-center justify-center gap-1.5 shadow-sm"
                    >
                      <Check className="w-3.5 h-3.5" />
                      <span>{t("mapModal.useThisLocation", locale)}</span>
                    </button>
                  </div>
                )}

                {/* Validate Button */}
                <button
                  type="button"
                  onClick={handleValidateManualInput}
                  className="w-full py-2.5 px-4 rounded-lg bg-base border border-brand-primary/40 text-brand-primary font-bold text-sm hover:bg-brand-primary/10 transition-colors flex items-center justify-center gap-2 shadow-xs"
                >
                  <Check className="w-4 h-4" />
                  <span>{t("mapModal.validateButton", locale)}</span>
                </button>
              </div>
            </div>

            <p className="text-[11px] text-ink-secondary text-center max-w-lg mx-auto">
              Latitude range: -90° to +90° | Longitude range: -180° to +180°
            </p>
          </div>
        )}

        {/* Modal Footer */}
        <div className="px-6 py-4 border-t border-ink-secondary/15 flex items-center justify-between bg-surface">
          <span className="text-xs text-ink-secondary font-medium">
            {position && typeof position.lat === "number" && typeof position.lon === "number"
              ? `${t("mapModal.selectedBadge", locale)} (${position.lat.toFixed(4)}°, ${position.lon.toFixed(4)}°)`
              : t("mapModal.clickPrompt", locale)}
          </span>
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-ink-secondary/30 text-ink-primary text-sm font-medium hover:bg-base transition-colors"
            >
              {t("mapModal.cancel", locale)}
            </button>
            <button
              onClick={handleConfirmLocation}
              disabled={!position || typeof position.lat !== "number" || typeof position.lon !== "number"}
              className="px-5 py-2 rounded-lg bg-brand-primary text-surface text-sm font-semibold hover:bg-brand-primary/90 disabled:opacity-40 transition-colors flex items-center gap-1.5 shadow-sm"
            >
              <Check className="w-4 h-4" />
              <span>{t("mapModal.confirm", locale)}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
