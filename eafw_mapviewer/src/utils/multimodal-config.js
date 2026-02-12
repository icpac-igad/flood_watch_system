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
  emergency: "Emergency",
  alarm: "Alarm",
  warning: "Warning",
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

export const buildMultimodalLegendItems = (colors = ALERT_COLORS) =>
  ALERT_LEVEL_ORDER.map((level) => ({
    name: getAlertLabel(level),
    color: colors[level] || ALERT_COLORS[level],
    level,
  }));

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
