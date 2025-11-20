/**
 * Data Transformation Utilities
 * Helper functions for processing and transforming map data
 */

/**
 * Parse time series discharge data into chart-ready format
 * @param {string} gfsData - Comma-separated GFS values
 * @param {string} iconData - Comma-separated ICON values
 * @param {Array} timestamps - Array of timestamp dates
 * @returns {Array} - Array of {time, gfs, icon} objects
 */
export function parseDischargeTimeSeries(gfsData, iconData, timestamps) {
  const gfsValues = gfsData ? gfsData.split(',').map(v => {
    const val = parseFloat(v);
    return (val === -9998 || isNaN(val)) ? null : val;
  }) : [];
  
  const iconValues = iconData ? iconData.split(',').map(v => {
    const val = parseFloat(v);
    return (val === -9998 || isNaN(val)) ? null : val;
  }) : [];
  
  const maxLength = Math.max(gfsValues.length, iconValues.length, timestamps?.length || 0);
  
  return Array.from({ length: maxLength }, (_, i) => ({
    time: timestamps?.[i] || new Date(),
    gfs: gfsValues[i] || null,
    icon: iconValues[i] || null,
  }));
}

/**
 * Extract valid numeric values from comma-separated string
 * Filters out invalid values (-9998, NaN)
 * @param {string} dataString - Comma-separated values
 * @returns {Array<number>} - Array of valid numbers
 */
export function extractValidValues(dataString) {
  if (!dataString) return [];
  
  return dataString
    .split(',')
    .map(v => parseFloat(v))
    .filter(v => v !== -9998 && !isNaN(v));
}

/**
 * Get latest valid value from time series
 * @param {string} dataString - Comma-separated values
 * @returns {number} - Latest valid value or 0
 */
export function getLatestValue(dataString) {
  const values = extractValidValues(dataString);
  return values.length > 0 ? values[values.length - 1] : 0;
}

/**
 * Format date for API requests (YYYYMMDD format)
 * @param {Date|string} date - Date object or string
 * @returns {string} - Formatted date string
 */
export function formatDateForAPI(date) {
  if (!date) return '';
  
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  const year = dateObj.getFullYear();
  const month = String(dateObj.getMonth() + 1).padStart(2, '0');
  const day = String(dateObj.getDate()).padStart(2, '0');
  
  return `${year}${month}${day}`;
}

/**
 * Format date for display (YYYY-MM-DD format)
 * @param {Date|string} date - Date object or string
 * @returns {string} - Formatted date string
 */
export function formatDateForDisplay(date) {
  if (!date) return '';
  
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return dateObj.toISOString().split('T')[0];
}

/**
 * Parse GeoSFM timestamp into JavaScript Date
 * @param {string} timestamp - Timestamp string
 * @returns {Date} - Date object
 */
export function parseGeoSFMTimestamp(timestamp) {
  return new Date(timestamp);
}

/**
 * Group features by country
 * @param {Array} features - GeoJSON features
 * @param {string} countryField - Property name for country (default: 'COUNTRY')
 * @returns {Object} - Object with country keys and feature arrays
 */
export function groupFeaturesByCountry(features, countryField = 'COUNTRY') {
  if (!features || features.length === 0) return {};
  
  return features.reduce((acc, feature) => {
    const country = feature.properties?.[countryField] || 'Unknown';
    if (!acc[country]) {
      acc[country] = [];
    }
    acc[country].push(feature);
    return acc;
  }, {});
}

/**
 * Calculate statistics for discharge values
 * @param {Array<number>} values - Array of discharge values
 * @returns {Object} - { min, max, mean, median }
 */
export function calculateDischargeStats(values) {
  if (!values || values.length === 0) {
    return { min: 0, max: 0, mean: 0, median: 0 };
  }
  
  const sorted = [...values].sort((a, b) => a - b);
  const min = sorted[0];
  const max = sorted[sorted.length - 1];
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const median = sorted.length % 2 === 0
    ? (sorted[sorted.length / 2 - 1] + sorted[sorted.length / 2]) / 2
    : sorted[Math.floor(sorted.length / 2)];
  
  return { min, max, mean, median };
}
