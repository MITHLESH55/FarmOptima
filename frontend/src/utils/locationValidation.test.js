import assert from "node:assert";
import test from "node:test";
import {
  parseCoordinate,
  validateLatitude,
  validateLongitude,
  validateCoordinates,
  formatCoordinates,
} from "./locationValidation.js";

test("parseCoordinate handles numbers, numeric strings, whitespace and invalid inputs", () => {
  assert.strictEqual(parseCoordinate(18.3926), 18.3926);
  assert.strictEqual(parseCoordinate(" 18.3926 "), 18.3926);
  assert.strictEqual(parseCoordinate("-73.8706"), -73.8706);
  assert.strictEqual(parseCoordinate("0"), 0);
  assert.strictEqual(parseCoordinate(""), null);
  assert.strictEqual(parseCoordinate(null), null);
  assert.strictEqual(parseCoordinate(undefined), null);
  assert.strictEqual(Number.isNaN(parseCoordinate("abc")), true);
  assert.strictEqual(Number.isNaN(parseCoordinate(NaN)), true);
  assert.strictEqual(Number.isNaN(parseCoordinate(Infinity)), true);
});

test("validateLatitude enforces [-90, 90] bounds", () => {
  assert.strictEqual(validateLatitude(0), true);
  assert.strictEqual(validateLatitude(90), true);
  assert.strictEqual(validateLatitude(-90), true);
  assert.strictEqual(validateLatitude(18.3926), true);
  assert.strictEqual(validateLatitude(-18.3926), true);
  assert.strictEqual(validateLatitude(90.0001), false);
  assert.strictEqual(validateLatitude(-90.0001), false);
  assert.strictEqual(validateLatitude(NaN), false);
  assert.strictEqual(validateLatitude("18"), false);
});

test("validateLongitude enforces [-180, 180] bounds", () => {
  assert.strictEqual(validateLongitude(0), true);
  assert.strictEqual(validateLongitude(180), true);
  assert.strictEqual(validateLongitude(-180), true);
  assert.strictEqual(validateLongitude(73.8706), true);
  assert.strictEqual(validateLongitude(-73.8706), true);
  assert.strictEqual(validateLongitude(180.0001), false);
  assert.strictEqual(validateLongitude(-180.0001), false);
  assert.strictEqual(validateLongitude(NaN), false);
  assert.strictEqual(validateLongitude("73"), false);
});

test("validateCoordinates handles various valid and invalid coordinate pairs", () => {
  // Valid pairs
  const valid1 = validateCoordinates("18.3926", "73.8706");
  assert.strictEqual(valid1.isValid, true);
  assert.strictEqual(valid1.lat, 18.3926);
  assert.strictEqual(valid1.lon, 73.8706);

  const valid2 = validateCoordinates("-18.3926", "-73.8706");
  assert.strictEqual(valid2.isValid, true);
  assert.strictEqual(valid2.lat, -18.3926);
  assert.strictEqual(valid2.lon, -73.8706);

  // Empty values
  const empty = validateCoordinates("", "73.8706");
  assert.strictEqual(empty.isValid, false);
  assert.strictEqual(empty.errorKey, "mapModal.errEmpty");

  // Non-numeric
  const nonNum = validateCoordinates("abc", "73.8706");
  assert.strictEqual(nonNum.isValid, false);
  assert.strictEqual(nonNum.errorKey, "mapModal.errInvalidNum");

  // Out of bounds lat
  const badLat = validateCoordinates("91", "73.8706");
  assert.strictEqual(badLat.isValid, false);
  assert.strictEqual(badLat.errorKey, "mapModal.errLatRange");

  // Out of bounds lon
  const badLon = validateCoordinates("18.3926", "181");
  assert.strictEqual(badLon.isValid, false);
  assert.strictEqual(badLon.errorKey, "mapModal.errLonRange");

  // Null Island (0, 0)
  const nullIsland = validateCoordinates("0", "0");
  assert.strictEqual(nullIsland.isValid, false);
  assert.strictEqual(nullIsland.errorKey, "mapModal.errNullIsland");
});

test("formatCoordinates formats coordinates clearly with cardinal directions", () => {
  assert.strictEqual(formatCoordinates(18.3926, 73.8706), "18.3926° N, 73.8706° E");
  assert.strictEqual(formatCoordinates(-18.3926, -73.8706), "18.3926° S, 73.8706° W");
  assert.strictEqual(formatCoordinates(0, 0), "0.0000° N, 0.0000° E");
});
