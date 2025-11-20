/**
 * Marker Cluster Configuration
 * Settings for how monitoring stations are clustered on the map
 */

export const MARKER_CLUSTER_CONFIG = {
  maxClusterRadius: 50,
  disableClusteringAtZoom: 15,
  spiderfyOnMaxZoom: false,
  showCoverageOnHover: false,
  spiderLegPolylineOptions: {
    weight: 1.5,
    color: '#222',
    opacity: 0.5,
  },
  spiderfyDistanceMultiplier: 1.5,
};

/**
 * Get alert status priority for clustering
 * Higher priority statuses take precedence
 */
export const ALERT_PRIORITY = {
  'Emergency': 4,
  'Alarm': 3,
  'Warning': 2,
  'Normal': 1,
};

/**
 * Determine cluster alert status based on child markers
 * @param {Array} markers - Array of child markers
 * @returns {string} - Highest severity alert status
 */
export function getClusterAlertStatus(markers) {
  const alertLevels = markers.map(marker => marker.alertStatus || 'Normal');
  
  // Count stations by alert level
  const emergencyCount = alertLevels.filter(level => level === 'Emergency').length;
  const alarmCount = alertLevels.filter(level => level === 'Alarm').length;
  const warningCount = alertLevels.filter(level => level === 'Warning').length;
  
  // Return highest severity
  if (emergencyCount > 0) return 'Emergency';
  if (alarmCount > 0) return 'Alarm';
  if (warningCount > 0) return 'Warning';
  return 'Normal';
}
