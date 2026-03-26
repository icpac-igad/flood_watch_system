export const PRODUCTION =
  process.env.FEATURE_ENV && process.env.FEATURE_ENV === "production";
export const CMS_API = process.env.CMS_API || "https://eahazardswatch.icpac.net/api";

export const DEFAULT_CENTER_LAT = parseFloat(process.env.DEFAULT_CENTER_LAT || 5.73)
export const DEFAULT_CENTER_LNG = parseFloat(process.env.DEFAULT_CENTER_LNG || 36.84)
export const DEFAULT_ZOOM_LEVEL = parseFloat(process.env.DEFAULT_ZOOM_LEVEL || 4)
export const DEFAULT_MIN_ZOOM = parseFloat(process.env.DEFAULT_MIN_ZOOM || 4)
