/**
 * API Endpoints Configuration
 * Centralized API URL management with environment variable support
 */

const getApiUrl = (): string => {
  const apiUrl = import.meta.env.VITE_API_URL || "__VITE_API_URL__";
  return apiUrl.startsWith('__') ? 'http://localhost:8090' : apiUrl;
};

const getFastApiUrl = (): string => {
  const fastApiUrl = import.meta.env.VITE_FASTAPI_URL || "__VITE_FASTAPI_URL__";
  return fastApiUrl.startsWith('__') ? 'http://localhost:9050' : fastApiUrl;
};

// MapServer/MapCache removed - replaced by TiPg (vectors) and TiTiler (rasters)
// TODO: Add TiTiler configuration when implemented
const getTiPgUrl = (): string => {
  // Use nginx proxy path for CORS compatibility
  return '/tipg';
};

/**
 * API Endpoints
 */
export const API_ENDPOINTS = {
  base: getApiUrl(),
  fastApi: getFastApiUrl(),

  // Forecast endpoints
  forecasts: {
    deterministic: {
      dates: `${getFastApiUrl()}/merged-forecast/dates/`,
      byDate: (date: string) => `${getFastApiUrl()}/merged-forecast/${date}/`,
      latest: `${getFastApiUrl()}/merged-forecast/latest/`,
    },
    geosfm: {
      dates: `${getApiUrl()}/geosfm/available-dates/`,
      byDate: (date: string) => `${getApiUrl()}/geosfm/${date}/`,
    },
    ensemble: `${getFastApiUrl()}/ensemble-control-points`,
  },
  
  // Boundary endpoints
  boundaries: {
    admin0: `${getApiUrl()}/admin0/`,
    admin1: `${getApiUrl()}/admin1/`,
    admin2: `${getApiUrl()}/admin2/`,
    waterbodies: `${getApiUrl()}/water-bodies/`,
  },

  // TiPg vector tiles - Active (replaces MapServer for vectors)
  tipg: {
    base: getTiPgUrl(),
    collections: `${getTiPgUrl()}/collections`,
  },

  // TODO: Add TiTiler raster endpoints when implemented
  // titiler: {
  //   base: '/titiler',
  //   cog: (url: string) => `/titiler/cog/tiles/{z}/{x}/{y}?url=${encodeURIComponent(url)}`,
  // },
} as const;

/**
 * Legacy exports for backward compatibility
 * TODO: Remove after complete migration
 */
export const API_BASE_URL = API_ENDPOINTS.base;
