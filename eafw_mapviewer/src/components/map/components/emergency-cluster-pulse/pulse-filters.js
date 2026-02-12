import { DEFAULT_BASE_RADIUS } from "./constants";

export const buildEmergencyFilter = () => [
  "any",
  [
    "==",
    ["downcase", ["to-string", ["coalesce", ["get", "alert_level"], ""]]],
    "emergency",
  ],
  [">", ["to-number", ["coalesce", ["get", "emergency_count"], 0]], 0],
];

export const buildPulseFilter = (baseFilter) => {
  const emergencyOnly = buildEmergencyFilter();
  if (!Array.isArray(baseFilter) || baseFilter.length === 0) return emergencyOnly;
  return ["all", baseFilter, emergencyOnly];
};

export const normalizeRadiusExpression = (radiusExpr) => {
  if (typeof radiusExpr === "number") return radiusExpr;
  if (Array.isArray(radiusExpr)) return radiusExpr;
  return DEFAULT_BASE_RADIUS;
};

const buildPointCountExpression = () => [
  "to-number",
  ["coalesce", ["get", "point_count"], 1],
];

export const buildPulseRadiusScaleExpression = () => [
  "interpolate",
  ["linear"],
  buildPointCountExpression(),
  1,
  1.0,
  5,
  1.2,
  15,
  1.45,
  40,
  1.8,
  80,
  2.3,
];

export const buildPulseOpacityScaleExpression = () => [
  "interpolate",
  ["linear"],
  buildPointCountExpression(),
  1,
  0.8,
  5,
  0.95,
  15,
  1.15,
  40,
  1.35,
  80,
  1.6,
];

export const buildPulseRadiusExpression = (baseRadiusExpr, pulseOffset) => [
  "+",
  normalizeRadiusExpression(baseRadiusExpr),
  ["*", pulseOffset, buildPulseRadiusScaleExpression()],
];

export const buildPulseOpacityExpression = (opacity) => [
  "min",
  0.95,
  ["*", opacity, buildPulseOpacityScaleExpression()],
];

export const buildPulseBlurExpression = () => [
  "interpolate",
  ["linear"],
  buildPointCountExpression(),
  1,
  0.62,
  10,
  0.56,
  40,
  0.5,
  80,
  0.45,
];

export const safeJsonStringify = (value) => {
  try {
    return JSON.stringify(value);
  } catch (e) {
    return "";
  }
};
