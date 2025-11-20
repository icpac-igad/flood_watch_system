/**
 * Popup Content Generators
 * Creates HTML strings for Leaflet map popups
 */

/**
 * Generate popup content for FloodProofs monitoring station
 * @param {Object} feature - GeoJSON feature with station properties
 * @param {string} alertStatus - Current alert status (Normal, Warning, Alarm, Emergency)
 * @param {number} discharge - Current discharge value in m³/s
 * @returns {string} - HTML string for popup
 */
export function createFloodProofsPopup(feature, alertStatus, discharge) {
  const props = feature.properties;
  
  const alertThreshold = parseFloat(props.Q_THR1 || 0);
  const alarmThreshold = parseFloat(props.Q_THR2 || 0);
  const emergencyThreshold = parseFloat(props.Q_THR3 || 0);
  
  return `
    <div class="station-popup">
      <strong>${props.SEC_NAME || "Station"}</strong><br/>
      <strong>Basin:</strong> ${props.BASIN || "N/A"}<br/>
      <strong>Status:</strong> ${alertStatus}<br/>
      <strong>Discharge:</strong> ${discharge.toFixed(2)} m³/s<br/>
      <strong>Thresholds:</strong><br/>
      &nbsp;&nbsp;Alert: ${alertThreshold.toFixed(1)} m³/s<br/>
      &nbsp;&nbsp;Alarm: ${alarmThreshold.toFixed(1)} m³/s<br/>
      &nbsp;&nbsp;Emergency: ${emergencyThreshold.toFixed(1)} m³/s<br/>
      <button 
        id="generate-report-btn" 
        style="margin-top: 10px; padding: 5px 15px; background-color: #1B6840; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; width: 100%;"
        onmouseover="this.style.backgroundColor='#145432'" 
        onmouseout="this.style.backgroundColor='#1B6840'"
      >
        📊 Generate Report
      </button>
    </div>
  `;
}

/**
 * Generate popup content for GeoSFM satellite monitoring point
 * @param {Object} feature - GeoJSON feature with GeoSFM properties
 * @returns {string} - HTML string for popup
 */
export function createGeoSFMPopup(feature) {
  const props = feature.properties;
  
  return `
    <div class="geofsm-popup">
      <strong>${props.Name || "GeoSFM Point"}</strong><br/>
      Description: ${props.Descriptio || "N/A"}<br/>
      Gridcode: ${props.Gridcode || "N/A"}<br/>
      Latitude: ${props.Y?.toFixed(4) || "N/A"}°N<br/>
      Longitude: ${props.X?.toFixed(4) || "N/A"}°E<br/>
      ID: ${props.Id || "N/A"}
    </div>
  `;
}

/**
 * Calculate current discharge from time series data
 * @param {Object} feature - GeoJSON feature with station properties
 * @returns {number} - Current discharge value
 */
export function calculateCurrentDischarge(feature) {
  const props = feature.properties;
  const gfsData = props["time_series_discharge_simulated-gfs"];
  const iconData = props["time_series_discharge_simulated-icon"];
  
  if (!gfsData && !iconData) {
    return 0;
  }
  
  let latestGfs = 0;
  let latestIcon = 0;
  
  if (gfsData) {
    const gfsValues = gfsData.split(",").map(val => Number(val.trim()) || 0);
    latestGfs = gfsValues[gfsValues.length - 1] || 0;
  }
  
  if (iconData) {
    const iconValues = iconData.split(",").map(val => Number(val.trim()) || 0);
    latestIcon = iconValues[iconValues.length - 1] || 0;
  }
  
  return Math.max(latestGfs, latestIcon);
}

/**
 * Attach popup open event listener for generate report button
 * @param {Object} layer - Leaflet layer
 * @param {Function} generateReport - Report generation callback
 * @param {Object} feature - GeoJSON feature data
 */
export function attachReportButtonListener(layer, generateReport, feature) {
  layer.on('popupopen', () => {
    const reportBtn = document.getElementById('generate-report-btn');
    if (reportBtn) {
      reportBtn.onclick = () => generateReport(feature);
    }
  });
}
