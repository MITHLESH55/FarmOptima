/**
 * Coordinate validation utility functions for FarmOptima
 */

export function parseCoordinate(value) {
  if (value === null || value === undefined) return null;
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (trimmed === "") return null;
    const parsed = Number(trimmed);
    return isNaN(parsed) || !isFinite(parsed) ? NaN : parsed;
  }
  if (typeof value === "number") {
    return isNaN(value) || !isFinite(value) ? NaN : value;
  }
  return NaN;
}

export function validateLatitude(lat) {
  return typeof lat === "number" && !isNaN(lat) && isFinite(lat) && lat >= -90 && lat <= 90;
}

export function validateLongitude(lon) {
  return typeof lon === "number" && !isNaN(lon) && isFinite(lon) && lon >= -180 && lon <= 180;
}

export function validateCoordinates(latInput, lonInput) {
  const parsedLat = parseCoordinate(latInput);
  const parsedLon = parseCoordinate(lonInput);

  if (parsedLat === null || isNaN(parsedLat)) {
    return {
      isValid: false,
      errorKey: "mapModal.errInvalidLat",
      lat: null,
      lon: null,
    };
  }

  if (parsedLon === null || isNaN(parsedLon)) {
    return {
      isValid: false,
      errorKey: "mapModal.errInvalidLon",
      lat: null,
      lon: null,
    };
  }

  if (!validateLatitude(parsedLat)) {
    return {
      isValid: false,
      errorKey: "mapModal.errLatRange",
      lat: null,
      lon: null,
    };
  }

  if (!validateLongitude(parsedLon)) {
    return {
      isValid: false,
      errorKey: "mapModal.errLonRange",
      lat: null,
      lon: null,
    };
  }

  return {
    isValid: true,
    errorKey: null,
    lat: parsedLat,
    lon: parsedLon,
  };
}

export function formatCoordinates(lat, lon) {
  if (typeof lat !== "number" || typeof lon !== "number" || isNaN(lat) || isNaN(lon)) {
    return "";
  }
  const latDir = lat >= 0 ? "N" : "S";
  const lonDir = lon >= 0 ? "E" : "W";
  return `${Math.abs(lat).toFixed(4)}° ${latDir}, ${Math.abs(lon).toFixed(4)}° ${lonDir}`;
}
