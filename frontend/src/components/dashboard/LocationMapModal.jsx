import React from "react";
import { MapContainer, TileLayer, Marker, useMapEvents } from "react-leaflet";
import L from "leaflet";
import { X, Check, MapPin } from "lucide-react";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";
import { t } from "../../i18n";

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

export default function LocationMapModal({ isOpen, onClose, position, onSelect, onConfirm, locale }) {
  if (!isOpen) return null;

  const center = position ? [position.lat, position.lon] : [20.5937, 78.9629]; // India default centroid

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink-primary/60 backdrop-blur-sm animate-fadeIn">
      <div className="bg-surface rounded-card shadow-2xl border border-ink-secondary/20 w-full max-w-4xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-ink-secondary/15 flex items-center justify-between bg-base">
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
            className="w-8 h-8 rounded-full flex items-center justify-center text-ink-secondary hover:text-ink-primary hover:bg-ink-secondary/10 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Map Container */}
        <div className="relative w-full h-[480px] bg-ink-secondary/10">
          <MapContainer
            center={center}
            zoom={position ? 12 : 5}
            style={{ height: "100%", width: "100%" }}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <ClickCapture onSelect={onSelect} />
            {position && <Marker position={[position.lat, position.lon]} icon={customIcon} />}
          </MapContainer>

          {/* Coordinate overlay badge */}
          {position && (
            <div className="absolute bottom-4 left-4 z-[400] bg-surface/90 backdrop-blur-md px-3 py-2 rounded-lg border border-ink-secondary/20 shadow-md text-xs font-semibold text-ink-primary flex items-center gap-2">
              <MapPin className="w-4 h-4 text-brand-accent" />
              <span>
                {t("common.latitude", locale)}: {position.lat.toFixed(4)}, {t("common.longitude", locale)}: {position.lon.toFixed(4)}
              </span>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 border-t border-ink-secondary/15 flex items-center justify-between bg-surface">
          <span className="text-xs text-ink-secondary">
            {position ? t("mapModal.selectedBadge", locale) : t("mapModal.clickPrompt", locale)}
          </span>
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-ink-secondary/30 text-ink-primary text-sm font-medium hover:bg-base transition-colors"
            >
              {t("mapModal.cancel", locale)}
            </button>
            <button
              onClick={() => {
                if (onConfirm) onConfirm(position);
                onClose();
              }}
              disabled={!position}
              className="px-5 py-2 rounded-lg bg-brand-primary text-surface text-sm font-semibold hover:bg-brand-primary/90 disabled:opacity-40 transition-colors flex items-center gap-1.5"
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
