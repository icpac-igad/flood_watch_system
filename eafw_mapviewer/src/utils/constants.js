export const PRODUCTION =
  process.env.FEATURE_ENV && process.env.FEATURE_ENV === "production";
export const CMS_API = process.env.CMS_API || "https://eahazardswatch.icpac.net/api";
// Admin boundaries come from CMS datasets (mukau-mapserver), not separate API
export const ADMIN_BOUNDARY_API = process.env.ADMIN_BOUNDARY_API || ""
