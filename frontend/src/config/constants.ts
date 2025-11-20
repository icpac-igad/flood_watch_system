/**
 * Application Constants
 * Global constants used throughout the application
 */

/**
 * Alert status types
 */
export const ALERT_STATUS = {
  NORMAL: 'Normal',
  WARNING: 'Warning',
  ALARM: 'Alarm',
  EMERGENCY: 'Emergency',
} as const;

export type AlertStatus = typeof ALERT_STATUS[keyof typeof ALERT_STATUS];

/**
 * Date format patterns
 */
export const DATE_FORMATS = {
  ISO: 'YYYY-MM-DD',
  DISPLAY: 'MMM DD, YYYY',
  API: 'YYYYMMDD',
} as const;

/**
 * Cache durations (in milliseconds)
 */
export const CACHE_DURATION = {
  FORECAST_DATA: 60 * 60 * 1000, // 1 hour
  AVAILABLE_DATES: 15 * 60 * 1000, // 15 minutes
  BOUNDARY_DATA: 24 * 60 * 60 * 1000, // 24 hours
} as const;

/**
 * Pagination defaults
 */
export const PAGINATION = {
  DEFAULT_PAGE_SIZE: 100,
  MAX_PAGE_SIZE: 1000,
} as const;

/**
 * Map animation durations (in seconds)
 */
export const ANIMATION_DURATION = {
  ZOOM: 0.5,
  PAN: 0.3,
  FADE: 0.2,
} as const;

/**
 * Feature flags
 */
export const FEATURES = {
  ENABLE_STAC_API: false, // Future: STAC API integration
  ENABLE_VECTOR_TILES: false, // Future: TiPg vector tiles
  ENABLE_OFFLINE_MODE: false,
} as const;

/**
 * East African countries
 */
export const COUNTRIES = [
  { code: 'BI', name: 'Burundi' },
  { code: 'DJ', name: 'Djibouti' },
  { code: 'ER', name: 'Eritrea' },
  { code: 'ET', name: 'Ethiopia' },
  { code: 'KE', name: 'Kenya' },
  { code: 'RW', name: 'Rwanda' },
  { code: 'SO', name: 'Somalia' },
  { code: 'SS', name: 'South Sudan' },
  { code: 'SD', name: 'Sudan' },
  { code: 'TZ', name: 'Tanzania' },
  { code: 'UG', name: 'Uganda' },
] as const;
