/**
 * Right Panel Component
 * Displays station summary and charts
 */

import { Box, Typography, IconButton } from "@mui/material";
import CloseIcon from '@mui/icons-material/Close';
import { DischargeChart, GeoSFMChart } from "../../utils/chart/chartUtils";

export const RightPanel = ({
  isVisible,
  onClose,
  selectedStation,
  timeSeriesData,
  geoFSMTimeSeriesData,
  chartType,
  selectedSeries,
  onSeriesChange,
  onDownloadCSV
}) => {
  // Calculate alert status
  const getAlertStatus = () => {
    if (!selectedStation) return 'normal';

    const props = selectedStation.properties;
    const dischargeGFS = props["time_series_discharge_simulated-gfs"];

    if (!dischargeGFS) return 'normal';

    const gfsValues = dischargeGFS.split(',')
      .map(v => parseFloat(v))
      .filter(v => v !== -9998 && !isNaN(v));

    const currentDischarge = gfsValues[gfsValues.length - 1] || 0;

    const alertThreshold = parseFloat(props.Q_THR1 || 0);
    const alarmThreshold = parseFloat(props.Q_THR2 || 0);
    const emergencyThreshold = parseFloat(props.Q_THR3 || 0);

    if (currentDischarge >= emergencyThreshold && emergencyThreshold > 0) {
      return 'emergency';
    } else if (currentDischarge >= alarmThreshold && alarmThreshold > 0) {
      return 'alarm';
    } else if (currentDischarge >= alertThreshold && alertThreshold > 0) {
      return 'warning';
    }

    return 'normal';
  };

  // Calculate current discharge
  const getCurrentDischarge = () => {
    if (!selectedStation) return 0;

    const dischargeGFS = selectedStation.properties["time_series_discharge_simulated-gfs"];
    if (!dischargeGFS) return 0;

    const gfsValues = dischargeGFS.split(',')
      .map(v => parseFloat(v))
      .filter(v => v !== -9998 && !isNaN(v));

    return gfsValues[gfsValues.length - 1] || 0;
  };

  const alertStatus = getAlertStatus();
  const currentDischarge = getCurrentDischarge();

  // Alert badge styles using Tailwind
  const getAlertBadgeClasses = (status) => {
    const baseClasses = "inline-block px-3 py-1 rounded-xl text-xs font-semibold uppercase";
    switch (status) {
      case 'normal':
        return `${baseClasses} bg-green-100 text-green-800`;
      case 'warning':
        return `${baseClasses} bg-yellow-100 text-yellow-800`;
      case 'alarm':
        return `${baseClasses} bg-red-100 text-red-800`;
      case 'emergency':
        return `${baseClasses} bg-red-200 text-red-900 font-bold`;
      default:
        return `${baseClasses} bg-gray-100 text-gray-800`;
    }
  };

  return (
    <>
      {/* Mobile Backdrop Overlay */}
      {isVisible && (
        <Box
          onClick={onClose}
          sx={{
            display: { xs: 'block', md: 'none' },
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            zIndex: 1199,
          }}
        />
      )}

      {/* Right Panel */}
      <Box
        className={`${isVisible ? 'translate-x-0' : 'translate-x-full'} transition-transform duration-300 ease-in-out`}
        sx={{
          width: {
            xs: '90%',
            sm: '380px',
            md: '400px'
          },
          maxWidth: {
            xs: '90%',
            md: '600px'
          },
          height: '100%',
          backgroundColor: '#ffffff',
          borderLeft: {
            xs: 'none',
            md: '2px solid rgba(0, 0, 0, 0.3)'
          },
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          position: 'fixed',
          right: 0,
          top: {
            xs: '60px',
            md: '80px'
          },
          bottom: '30px',
          zIndex: {
            xs: 1200,
            md: 999
          },
          boxShadow: {
            xs: isVisible ? '-2px 0 8px rgba(0,0,0,0.15)' : 'none',
            md: isVisible ? '-2px 0 8px rgba(0,0,0,0.1)' : 'none'
          }
        }}
      >
      {/* Header */}
      <Box
        sx={{
          p: 2,
          bgcolor: '#034930',
          color: 'white',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid #dee2e6',
          width: '100%',
          boxSizing: 'border-box',
        }}
      >
        <Typography variant="h6" sx={{ fontSize: 16, fontWeight: 600, m: 0, color: 'white' }}>
          Station Details
        </Typography>
        {selectedStation && (
          <IconButton
            onClick={onClose}
            sx={{
              color: 'white',
              '&:hover': {
                backgroundColor: 'rgba(255, 255, 255, 0.2)'
              }
            }}
            size="small"
          >
            <CloseIcon />
          </IconButton>
        )}
      </Box>

      {/* Content */}
      <Box
        sx={{
          flex: 1,
          overflowY: 'auto',
          overflowX: 'hidden',
          p: 2,
          '&::-webkit-scrollbar': {
            width: '8px'
          },
          '&::-webkit-scrollbar-track': {
            bgcolor: 'grey.100'
          },
          '&::-webkit-scrollbar-thumb': {
            bgcolor: 'grey.400',
            borderRadius: '4px',
            '&:hover': {
              bgcolor: 'grey.500'
            }
          }
        }}
      >
        {selectedStation ? (
          <>
            {/* Station Summary */}
            <div className="bg-gray-50 rounded-lg p-4 mb-4">
              <h4 className="m-0 mb-3 text-lg font-semibold text-[#1B6840]">
                {selectedStation.properties.SEC_NAME || "Unknown Station"}
              </h4>

              <div className="grid grid-cols-2 gap-3">
                <div className="flex flex-col">
                  <span className="text-xs text-gray-600 font-medium mb-1 uppercase">Basin</span>
                  <span className="text-base font-semibold text-gray-900">
                    {selectedStation.properties.BASIN || "N/A"}
                  </span>
                </div>

                <div className="flex flex-col">
                  <span className="text-xs text-gray-600 font-medium mb-1 uppercase">Status</span>
                  <span className={getAlertBadgeClasses(alertStatus)}>
                    {alertStatus}
                  </span>
                </div>

                <div className="flex flex-col">
                  <span className="text-xs text-gray-600 font-medium mb-1 uppercase">Current Discharge</span>
                  <span className="text-base font-semibold text-gray-900">{currentDischarge.toFixed(2)} m³/s</span>
                </div>

                <div className="flex flex-col">
                  <span className="text-xs text-gray-600 font-medium mb-1 uppercase">Alert Threshold</span>
                  <span className="text-base font-semibold text-gray-900">
                    {parseFloat(selectedStation.properties.Q_THR1 || 0).toFixed(1)} m³/s
                  </span>
                </div>

                <div className="flex flex-col">
                  <span className="text-xs text-gray-600 font-medium mb-1 uppercase">Alarm Threshold</span>
                  <span className="text-base font-semibold text-gray-900">
                    {parseFloat(selectedStation.properties.Q_THR2 || 0).toFixed(1)} m³/s
                  </span>
                </div>

                <div className="flex flex-col">
                  <span className="text-xs text-gray-600 font-medium mb-1 uppercase">Emergency Threshold</span>
                  <span className="text-base font-semibold text-gray-900">
                    {parseFloat(selectedStation.properties.Q_THR3 || 0).toFixed(1)} m³/s
                  </span>
                </div>
              </div>
            </div>

            {/* Chart Section */}
            <div className="bg-white rounded-lg border border-gray-300 p-4 mb-4">
              <h5 className="m-0 mb-4 text-sm font-semibold text-gray-700">Discharge Forecast</h5>

              {chartType === "discharge" && timeSeriesData && timeSeriesData.length > 0 ? (
                <>
                  {/* Series Selection */}
                  <div className="mb-4">
                    <label className="text-sm mr-2 text-gray-700">Show:</label>
                    <select
                      value={selectedSeries}
                      onChange={(e) => onSeriesChange(e.target.value)}
                      className="px-3 py-1.5 rounded border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="both">GFS + ICON</option>
                      <option value="gfs">GFS only</option>
                      <option value="icon">ICON only</option>
                    </select>
                  </div>

                  {/* Chart */}
                  <DischargeChart
                    timeSeriesData={timeSeriesData}
                    selectedSeries={selectedSeries}
                    stationName={selectedStation?.properties?.SEC_NAME || 'Station'}
                    height={300}
                  />

                  {/* Download Button */}
                  <button
                    onClick={onDownloadCSV}
                    className="mt-3 px-4 py-2 bg-[#034930] text-white rounded cursor-pointer text-sm w-full hover:bg-[#023020] transition-colors"
                  >
                    Download CSV
                  </button>
                </>
              ) : chartType === "riverdepth" || chartType === "streamflow" ? (
                <GeoSFMChart
                  timeSeriesData={geoFSMTimeSeriesData}
                  dataType={chartType}
                  stationName={selectedStation?.properties?.Name || selectedStation?.properties?.Descriptio || 'GeoSFM Station'}
                  height={300}
                />
              ) : (
                <div className="text-center py-8 text-gray-600">
                  <p>No chart data available</p>
                </div>
              )}
            </div>
          </>
        ) : (
          /* Empty State */
          <div className="flex flex-col items-center justify-center h-full text-center text-gray-600 px-8">
            <div className="text-5xl mb-4 opacity-50">📊</div>
            <div className="text-base mb-2">No Station Selected</div>
            <div className="text-sm opacity-70">
              Click on a monitoring station on the map to view details
            </div>
          </div>
        )}
      </Box>
      </Box>
    </>
  );
};
