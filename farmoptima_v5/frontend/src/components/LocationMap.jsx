import { MapContainer, TileLayer, Marker, useMapEvents } from "react-leaflet";
import L from "leaflet";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

// Leaflet's default marker icon paths break under bundlers — fix explicitly.
const icon = L.icon({
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

export default function LocationMap({ position, onSelect }) {
  const center = position ? [position.lat, position.lon] : [20.5937, 78.9629]; // India centroid default

  return (
    <div className="rounded-xl overflow-hidden border" style={{ borderColor: "var(--line)" }}>
      <MapContainer center={center} zoom={position ? 11 : 5} style={{ height: "420px", width: "100%" }}>
        <TileLayer
          attribution='&copy; OpenStreetMap contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <ClickCapture onSelect={onSelect} />
        {position && <Marker position={[position.lat, position.lon]} icon={icon} />}
      </MapContainer>
    </div>
  );
}
