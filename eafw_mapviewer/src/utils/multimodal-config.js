/**
 * Shared configuration for multimodal forecast visualization
 * Single source of truth for thresholds, colors, and alert level calculation
 *
 * Both the cluster layer and chart component import from here to ensure consistency
 */

// =============================================================================
// DEFAULT THRESHOLDS (can be overridden by CMS config)
// =============================================================================

export const DEFAULT_THRESHOLDS = {
  warning: 300,      // >= 300 m³/s
  alarm: 500,        // >= 500 m³/s
  emergency: 750,    // >= 750 m³/s
};

// =============================================================================
// ALERT COLORS - used for point markers and badges
// =============================================================================

export const ALERT_COLORS = {
  normal: "#b0bec5",
  warning: "#b8f0f0",    // Moderate — light cyan
  alarm: "#2f83d2",      // Severe — blue
  emergency: "#1e1a97",  // Extreme — deep blue
};

export const ALERT_LEVEL_ORDER = ["emergency", "alarm", "warning", "normal"];

export const ALERT_LEVEL_LABELS = {
  emergency: "Extreme",
  alarm: "Severe",
  warning: "Moderate",
  normal: "Normal",
};

// =============================================================================
// ALERT PRIORITY - for cluster aggregation (higher = more severe)
// =============================================================================

export const ALERT_PRIORITY = {
  normal: 1,
  warning: 2,
  alarm: 3,
  emergency: 4,
};

// =============================================================================
// ICON NAMES - for symbol layer icon-image expressions
// Must match CMS VectorTileLayerIcon names (loaded via vectorLayerIcons)
// =============================================================================

export const ALERT_ICON_NAMES = {
  // Use dedicated IDs to avoid collisions with sprite/default CMS icon names.
  normal: "forecast-pin-v2-icon-normal",
  warning: "forecast-pin-v2-icon-warning",
  alarm: "forecast-pin-v2-icon-alarm",
  emergency: "forecast-pin-v2-icon-emergency",
};

// Cluster icon names (generated at runtime on canvas)
export const CLUSTER_ICON_PREFIX = "forecast-cluster-";

// Symbol layer layout defaults
export const SYMBOL_LAYOUT = {
  pointIconSize: 0.6,
  clusterIconSize: 0.7,
  clusterTextSize: 12,
  clusterTextColor: "#ffffff",
  clusterTextHaloColor: "rgba(0,0,0,0.7)",
  clusterTextHaloWidth: 1.2,
};

// =============================================================================
// WATER VISUALIZATION COLORS - for chart area fills
// =============================================================================

export const WATER_COLORS = {
  normal: { stroke: "#87CEEB", fill: "rgba(135, 206, 235, 0.3)" },
  warning: { stroke: "#b8f0f0", fill: "rgba(184, 240, 240, 0.4)" },
  alarm: { stroke: "#2f83d2", fill: "rgba(47, 131, 210, 0.5)" },
  emergency: { stroke: "#1e1a97", fill: "rgba(30, 26, 151, 0.6)" },
};

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

/**
 * Get today's date string in YYYY-MM-DD format
 * @returns {string} Today's date
 */
export const getTodayStr = () => {
  const today = new Date();
  return today.toISOString().split("T")[0];
};

/**
 * Calculate alert level from daily_avg value and thresholds
 * @param {number} dailyAvg - The daily average discharge value
 * @param {object} thresholds - Threshold values {warning, alarm, emergency}
 * @returns {string} Alert level: 'emergency' | 'alarm' | 'warning' | 'normal'
 */
export const calculateAlertLevel = (dailyAvg, thresholds = DEFAULT_THRESHOLDS) => {
  const value = parseFloat(dailyAvg) || 0;

  if (value >= thresholds.emergency) return "emergency";
  if (value >= thresholds.alarm) return "alarm";
  if (value >= thresholds.warning) return "warning";
  return "normal";
};

/**
 * Calculate alert level from forecast array using a specific date's daily_avg
 * @param {Array} forecasts - Array of forecast objects with date and daily_avg
 * @param {object} thresholds - Threshold values {warning, alarm, emergency}
 * @param {string} targetDate - Optional date string (YYYY-MM-DD) to use, defaults to today
 * @returns {string} Alert level based on the target date's value
 */
export const calculateAlertLevelFromForecasts = (forecasts, thresholds = DEFAULT_THRESHOLDS, targetDate = null) => {
  if (!forecasts || !Array.isArray(forecasts) || forecasts.length === 0) {
    return "normal";
  }

  // Use provided date or default to today
  const dateStr = targetDate || getTodayStr();

  // Find the forecast for the target date
  const targetForecast = forecasts.find((f) => {
    if (!f.date) return false;
    const forecastDate = f.date.split("T")[0];
    return forecastDate === dateStr;
  });

  // Use target date's value, or fallback to first day if not found
  const dailyAvg = parseFloat(targetForecast?.daily_avg ?? forecasts[0]?.daily_avg) || 0;

  return calculateAlertLevel(dailyAvg, thresholds);
};

/**
 * Get color for an alert level
 * @param {string} level - Alert level
 * @returns {string} Hex color code
 */
export const getAlertColor = (level) => {
  return ALERT_COLORS[level?.toLowerCase()] || ALERT_COLORS.normal;
};

export const getAlertLabel = (level) => {
  return ALERT_LEVEL_LABELS[level?.toLowerCase()] || ALERT_LEVEL_LABELS.normal;
};

// Flood SVG path (flag with water waves — from humanitarian "flood" icon)
const STORM_SVG_PATH_D = "M47.82 12L33.16.06a.243.243 0 0 0-.32 0L18.18 12a.528.528 0 0 0-.18.38v17.71a8.734 8.734 0 0 1 3.29 1.15A4.637 4.637 0 0 0 24 32a4.626 4.626 0 0 0 2.7-.76A8.644 8.644 0 0 1 31.33 30a8.603 8.603 0 0 1 4.62 1.24 5.23 5.23 0 0 0 5.43 0A8.603 8.603 0 0 1 46 30a9.43 9.43 0 0 1 2 .2V12.38a.528.528 0 0 0-.18-.38zM46 42a8.603 8.603 0 0 0-4.62 1.24 5.23 5.23 0 0 1-5.43 0A8.603 8.603 0 0 0 31.33 42a8.644 8.644 0 0 0-4.63 1.24A4.626 4.626 0 0 1 24 44a4.637 4.637 0 0 1-2.71-.76A8.673 8.673 0 0 0 16.66 42a8.603 8.603 0 0 0-4.62 1.24 4.684 4.684 0 0 1-2.71.76 4.684 4.684 0 0 1-2.71-.76A8.603 8.603 0 0 0 2 42a2 2 0 0 0 0 4 4.683 4.683 0 0 1 2.71.76A8.604 8.604 0 0 0 9.33 48a8.603 8.603 0 0 0 4.62-1.24 4.684 4.684 0 0 1 2.71-.76 4.66 4.66 0 0 1 2.71.76A8.644 8.644 0 0 0 24 48a8.632 8.632 0 0 0 4.62-1.24 5.212 5.212 0 0 1 5.42 0 9.245 9.245 0 0 0 9.25 0A4.66 4.66 0 0 1 46 46a2 2 0 0 0 0-4zM46 34a8.59 8.59 0 0 0-4.625 1.244 5.241 5.241 0 0 1-5.423 0A8.59 8.59 0 0 0 31.326 34a8.581 8.581 0 0 0-4.623 1.244 4.692 4.692 0 0 1-2.708.756 4.696 4.696 0 0 1-2.709-.756A8.59 8.59 0 0 0 16.661 34a8.588 8.588 0 0 0-4.624 1.244A4.692 4.692 0 0 1 9.33 36a4.69 4.69 0 0 1-2.706-.755A8.577 8.577 0 0 0 2 34a2 2 0 0 0 0 4 4.691 4.691 0 0 1 2.707.756A8.58 8.58 0 0 0 9.329 40a8.588 8.588 0 0 0 4.624-1.244A4.692 4.692 0 0 1 16.661 38a4.696 4.696 0 0 1 2.71.756A8.59 8.59 0 0 0 23.994 40a8.583 8.583 0 0 0 4.624-1.245 5.236 5.236 0 0 1 5.42 0 9.22 9.22 0 0 0 9.25 0A4.702 4.702 0 0 1 46 38a2 2 0 0 0 0-4z";

const buildStormSvg = (color = ALERT_COLORS.normal, size = 28) => `
<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 48 48">
  <path d="${STORM_SVG_PATH_D}" fill="${color}"/>
</svg>
`;

export const getStormIconDataUri = (color = ALERT_COLORS.normal, size = 28) => {
  const svg = buildStormSvg(color || ALERT_COLORS.normal, size).trim();
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
};

// Keep pin exports for backward compatibility but they now use storm icon
export const getAlertPinIconDataUri = (color) => getStormIconDataUri(color, 24);

export const createAlertPinImageData = () => {
  // Not used for storm SVG approach — kept for API compat
  return null;
};

/**
 * Load a storm SVG icon into a MapLibre map via Image().
 * @param {object} map - MapLibre map instance
 * @param {string} iconId - ID for map.addImage()
 * @param {string} color - Fill color
 * @param {number} size - Icon size in pixels
 * @returns {Promise<void>}
 */
export const loadStormIconToMap = (map, iconId, color, size = 28) => {
  return new Promise((resolve) => {
    if (map.hasImage(iconId)) {
      try { map.removeImage(iconId); } catch (_) { /* ignore */ }
    }
    const img = new Image();
    img.onload = () => {
      map.addImage(iconId, img);
      resolve();
    };
    img.onerror = () => resolve();
    img.src = getStormIconDataUri(color, size);
  });
};

export const buildMultimodalLegendItems = (
  colors = ALERT_COLORS,
  options = {}
) => {
  const { includePinIcon = false, iconWidth = 12, iconHeight = 16 } = options;

  return ALERT_LEVEL_ORDER.map((level) => {
    const color = colors[level] || ALERT_COLORS[level];
    const item = {
      name: getAlertLabel(level),
      color,
      level,
    };

    if (includePinIcon) {
      item.icon = getAlertPinIconDataUri(color);
      item.iconWidth = iconWidth;
      item.iconHeight = iconHeight;
    }

    return item;
  });
};

/**
 * Get priority for an alert level (for cluster aggregation)
 * @param {string} level - Alert level
 * @returns {number} Priority value
 */
export const getAlertPriority = (level) => {
  return ALERT_PRIORITY[level?.toLowerCase()] || ALERT_PRIORITY.normal;
};

/**
 * Get water visualization colors for an alert level
 * @param {string} level - Alert level
 * @returns {object} {stroke, fill} colors
 */
export const getWaterColors = (level) => {
  return WATER_COLORS[level?.toLowerCase()] || WATER_COLORS.normal;
};

/**
 * Merge CMS config with defaults
 * @param {object} cmsConfig - Configuration from CMS
 * @returns {object} Merged configuration
 */
export const mergeConfig = (cmsConfig = {}) => {
  return {
    thresholds: {
      ...DEFAULT_THRESHOLDS,
      ...(cmsConfig?.thresholds || {}),
    },
    colors: {
      ...ALERT_COLORS,
      ...(cmsConfig?.colors || {}),
    },
  };
};
