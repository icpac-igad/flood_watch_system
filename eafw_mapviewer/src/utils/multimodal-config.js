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
  normal: "#b0b0b0",
  warning: "#ffc107",
  alarm: "#ff9800",
  emergency: "#d32f2f",
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
  normal: "normal",
  warning: "warning",
  alarm: "alarm",
  emergency: "emergency",
};

// Cluster icon names (generated at runtime on canvas)
export const CLUSTER_ICON_PREFIX = "cluster-";

// Symbol layer layout defaults
export const SYMBOL_LAYOUT = {
  pointIconSize: 0.45,
  clusterIconSize: 0.55,
  clusterTextSize: 11,
  clusterTextColor: "#ffffff",
  clusterTextHaloColor: "rgba(0,0,0,0.7)",
  clusterTextHaloWidth: 1.2,
};

// =============================================================================
// WATER VISUALIZATION COLORS - for chart area fills
// =============================================================================

export const WATER_COLORS = {
  normal: { stroke: "#87CEEB", fill: "rgba(135, 206, 235, 0.3)" },
  warning: { stroke: "#4A90D9", fill: "rgba(74, 144, 217, 0.4)" },
  alarm: { stroke: "#1E5AA8", fill: "rgba(30, 90, 168, 0.5)" },
  emergency: { stroke: "#0D3B6B", fill: "rgba(13, 59, 107, 0.6)" },
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

// Storm SVG path (cloud with lightning bolt — from Wagtail "storm" icon)
const STORM_SVG_PATH_D = "M38.98 9.01a8.732 8.732 0 0 0-3.16.58l-.01.005a11.49 11.49 0 0 0-22.823 1.757 5.977 5.977 0 0 0-7.91 6.69l-.007-.002a3.81 3.81 0 0 0-.59-.04 4.5 4.5 0 0 0 0 9h34.5a9.003 9.003 0 0 0 8.83-7.24 9.297 9.297 0 0 0 .17-1.76 8.992 8.992 0 0 0-9-8.99zM28.48 37h-6.293l3.565-5.705a1.5 1.5 0 1 0-2.544-1.59l-5 8A1.5 1.5 0 0 0 19.48 40h6.293l-3.565 5.705a1.5 1.5 0 1 0 2.544 1.59l5-8A1.5 1.5 0 0 0 28.48 37z";

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
