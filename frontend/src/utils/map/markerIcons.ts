import L from 'leaflet';
import { AlertStatus } from '../../types/map.types';

// Color mapping for alert statuses
const COLOR_MAP: Record<AlertStatus, { bg: string; border: string }> = {
  'Normal': { bg: '#9E9E9E', border: '#616161' },      // Gray
  'Warning': { bg: '#FFA726', border: '#F57C00' },     // Orange  
  'Alarm': { bg: '#FF5722', border: '#E64A19' },       // Deep Orange
  'Emergency': { bg: '#B71C1C', border: '#7F0000' }    // Dark Red
};

/**
 * Creates a balloon/pin-style marker icon based on alert status
 * @param alertStatus - The alert status of the station
 * @param isCluster - Whether this is a cluster marker
 * @param _clusterCount - Number of stations in cluster (unused, kept for API compatibility)
 * @param isSelected - Whether the marker is selected
 */
export const getMarkerIcon = (
  alertStatus: AlertStatus = 'Normal',
  isCluster: boolean = false,
  _clusterCount: number = 0,
  isSelected: boolean = false
): L.DivIcon => {
  const colors = COLOR_MAP[alertStatus] || COLOR_MAP['Normal'];
  
  // BOTH clusters and individual markers use balloon shape
  const width = isCluster ? 32 : (isSelected ? 28 : 24);
  const height = isCluster ? 42 : (isSelected ? 36 : 30);
  const blinkClass = alertStatus !== 'Normal' ? `marker-${alertStatus.toLowerCase()}` : '';
  const className = [isCluster ? 'cluster-balloon' : '', isSelected ? 'selected-marker' : '', blinkClass].filter(Boolean).join(' ');
  
  return L.divIcon({
    html: `
      <svg width="${width}" height="${height}" viewBox="0 0 24 36" xmlns="http://www.w3.org/2000/svg" style="filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));">
        <!-- Balloon pin shape -->
        <path d="M12 0C7.6 0 4 3.6 4 8c0 5.4 8 20 8 20s8-14.6 8-20c0-4.4-3.6-8-8-8z" 
              fill="${colors.bg}"/>
      </svg>
    `,
    className: className,
    iconSize: [width, height],
    iconAnchor: [width/2, height],
    popupAnchor: [0, -height + 5]
  });
};
