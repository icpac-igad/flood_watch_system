/**
 * Animation Styles for Map Markers
 * Blinking animations for different alert levels
 */

/**
 * Inject animation styles into document head
 * Call this once when the app initializes
 */
export function injectMarkerAnimations() {
  // Check if already injected
  if (document.getElementById('marker-animations')) {
    return;
  }

  const style = document.createElement('style');
  style.id = 'marker-animations';
  style.innerHTML = `
    @keyframes blink-warning {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }
    
    @keyframes blink-alarm {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.3; }
    }
    
    @keyframes blink-emergency {
      0%, 100% { opacity: 1; }
      25% { opacity: 0.2; }
      50% { opacity: 1; }
      75% { opacity: 0.2; }
    }
    
    .marker-warning, .cluster-warning {
      animation: blink-warning 2s infinite;
    }
    
    .marker-alarm, .cluster-alarm {
      animation: blink-alarm 1.5s infinite;
    }
    
    .marker-emergency, .cluster-emergency {
      animation: blink-emergency 1s infinite;
    }
    
    @keyframes spin {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }
  `;
  
  document.head.appendChild(style);
}

/**
 * Animation durations for different alert levels (in ms)
 */
export const ANIMATION_DURATIONS = {
  warning: 2000,
  alarm: 1500,
  emergency: 1000,
};

/**
 * Get animation class name for alert status
 * @param {string} alertStatus - Alert status (Normal, Warning, Alarm, Emergency)
 * @param {boolean} isCluster - Whether this is a cluster marker
 * @returns {string} - CSS class name for animation
 */
export function getAnimationClass(alertStatus, isCluster = false) {
  const prefix = isCluster ? 'cluster' : 'marker';
  const status = alertStatus.toLowerCase();
  
  if (status === 'warning' || status === 'alarm' || status === 'emergency') {
    return `${prefix}-${status}`;
  }
  
  return '';
}
