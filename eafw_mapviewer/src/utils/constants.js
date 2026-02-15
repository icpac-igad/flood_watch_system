export const PRODUCTION =
  process.env.FEATURE_ENV && process.env.FEATURE_ENV === "production";
export const CMS_API = process.env.CMS_API || "/api";
// FastAPI v1 base URL (all migrated endpoints)
export const FASTAPI_API = process.env.NEXT_PUBLIC_FASTAPI_API || "/api/v1";
// Admin boundaries served by FastAPI
export const ADMIN_BOUNDARY_API = process.env.ADMIN_BOUNDARY_API || "/api/v1/boundaries/admin-boundaries/";
// FastAPI reports endpoint (for flood analysis PDF and report APIs)
export const REPORTS_API = process.env.NEXT_PUBLIC_REPORTS_API || "/api/v1/reports";
