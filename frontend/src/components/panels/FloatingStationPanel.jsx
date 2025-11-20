/**
 * FloatingStationPanel Component
 * A draggable, floating panel that displays station information and charts on the map
 */

import { useState, useEffect, useRef } from 'react';
import { Box, Typography, IconButton, Collapse } from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import MinimizeIcon from '@mui/icons-material/Minimize';
import MaximizeIcon from '@mui/icons-material/Maximize';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import { DischargeChart, GeoSFMChart } from '../../utils/chart/chartUtils';

export const FloatingStationPanel = ({
  isVisible,
  onClose,
  selectedStation,
  timeSeriesData,
  geoFSMTimeSeriesData,
  chartType,
  selectedSeries,
  onSeriesChange,
  onDownloadCSV,
  markerPosition // { x, y } - pixel coordinates of the clicked marker
}) => {
  const [isMinimized, setIsMinimized] = useState(false);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const panelRef = useRef(null);

  // Position the panel near the clicked marker when it opens
  useEffect(() => {
    if (isVisible && markerPosition) {
      // Offset the panel slightly from the marker
      const offsetX = 20;
      const offsetY = -100;

      // Get viewport dimensions
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;

      // Panel dimensions (approximate)
      const panelWidth = 380;
      const panelHeight = isMinimized ? 60 : 500;

      // Calculate initial position, ensuring it stays within viewport
      let x = markerPosition.x + offsetX;
      let y = markerPosition.y + offsetY;

      // Adjust if panel would go off-screen
      if (x + panelWidth > viewportWidth - 20) {
        x = markerPosition.x - panelWidth - offsetX;
      }
      if (y < 100) {
        y = 100;
      }
      if (y + panelHeight > viewportHeight - 50) {
        y = viewportHeight - panelHeight - 50;
      }

      setPosition({ x, y });
    }
  }, [isVisible, markerPosition, isMinimized]);

  // Custom drag handlers (React 19 compatible)
  const handleMouseDown = (e) => {
    if (e.target.closest('.drag-handle')) {
      setIsDragging(true);
      setDragOffset({
        x: e.clientX - position.x,
        y: e.clientY - position.y
      });
    }
  };

  const handleMouseMove = (e) => {
    if (isDragging) {
      setPosition({
        x: e.clientX - dragOffset.x,
        y: e.clientY - dragOffset.y
      });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Add/remove global event listeners for dragging
  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      return () => {
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, dragOffset]);

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

  // Alert badge styles
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

  if (!isVisible || !selectedStation) return null;

  return (
    <Box
      ref={panelRef}
      onMouseDown={handleMouseDown}
      sx={{
        position: 'fixed',
        left: `${position.x}px`,
        top: `${position.y}px`,
        width: {
          xs: '90%',
          sm: '380px'
        },
        maxWidth: '500px',
        maxHeight: isMinimized ? 'auto' : '80vh',
        backgroundColor: '#ffffff',
        borderRadius: '8px',
        boxShadow: '0 4px 20px rgba(0,0,0,0.25)',
        border: '2px solid #034930',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        zIndex: 1300,
        cursor: 'default',
        userSelect: isDragging ? 'none' : 'auto'
      }}
    >
        {/* Header with drag handle */}
        <Box
          className="drag-handle"
          sx={{
            p: 1.5,
            bgcolor: '#034930',
            color: 'white',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            cursor: 'move',
            userSelect: 'none'
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <DragIndicatorIcon sx={{ fontSize: 20, opacity: 0.7 }} />
            <Typography variant="h6" sx={{ fontSize: 14, fontWeight: 600, m: 0 }}>
              Station Details
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 0.5 }}>
            <IconButton
              onClick={() => setIsMinimized(!isMinimized)}
              sx={{
                color: 'white',
                p: 0.5,
                '&:hover': {
                  backgroundColor: 'rgba(255, 255, 255, 0.2)'
                }
              }}
              size="small"
            >
              {isMinimized ? <MaximizeIcon sx={{ fontSize: 18 }} /> : <MinimizeIcon sx={{ fontSize: 18 }} />}
            </IconButton>
            <IconButton
              onClick={onClose}
              sx={{
                color: 'white',
                p: 0.5,
                '&:hover': {
                  backgroundColor: 'rgba(255, 255, 255, 0.2)'
                }
              }}
              size="small"
            >
              <CloseIcon sx={{ fontSize: 18 }} />
            </IconButton>
          </Box>
        </Box>

        {/* Content - Collapsible */}
        <Collapse in={!isMinimized}>
          <Box
            sx={{
              maxHeight: 'calc(80vh - 50px)',
              overflowY: 'auto',
              overflowX: 'hidden',
              p: 2,
              '&::-webkit-scrollbar': {
                width: '6px'
              },
              '&::-webkit-scrollbar-track': {
                bgcolor: 'grey.100'
              },
              '&::-webkit-scrollbar-thumb': {
                bgcolor: 'grey.400',
                borderRadius: '3px',
                '&:hover': {
                  bgcolor: 'grey.500'
                }
              }
            }}
          >
            {/* Station Summary */}
            <div className="bg-gray-50 rounded-lg p-3 mb-3">
              <h4 className="m-0 mb-3 text-base font-semibold text-[#1B6840]">
                {selectedStation.properties.SEC_NAME || "Unknown Station"}
              </h4>

              <div className="grid grid-cols-2 gap-2">
                <div className="flex flex-col">
                  <span className="text-xs text-gray-600 font-medium mb-1 uppercase">Basin</span>
                  <span className="text-sm font-semibold text-gray-900">
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
                  <span className="text-sm font-semibold text-gray-900">{currentDischarge.toFixed(2)} m³/s</span>
                </div>

                <div className="flex flex-col">
                  <span className="text-xs text-gray-600 font-medium mb-1 uppercase">Alert Threshold</span>
                  <span className="text-sm font-semibold text-gray-900">
                    {parseFloat(selectedStation.properties.Q_THR1 || 0).toFixed(1)} m³/s
                  </span>
                </div>

                <div className="flex flex-col">
                  <span className="text-xs text-gray-600 font-medium mb-1 uppercase">Alarm Threshold</span>
                  <span className="text-sm font-semibold text-gray-900">
                    {parseFloat(selectedStation.properties.Q_THR2 || 0).toFixed(1)} m³/s
                  </span>
                </div>

                <div className="flex flex-col">
                  <span className="text-xs text-gray-600 font-medium mb-1 uppercase">Emergency Threshold</span>
                  <span className="text-sm font-semibold text-gray-900">
                    {parseFloat(selectedStation.properties.Q_THR3 || 0).toFixed(1)} m³/s
                  </span>
                </div>
              </div>
            </div>

            {/* Chart Section */}
            <div className="bg-white rounded-lg border border-gray-300 p-3 mb-3">
              <h5 className="m-0 mb-3 text-sm font-semibold text-gray-700">Discharge Forecast</h5>

              {chartType === "discharge" && timeSeriesData && timeSeriesData.length > 0 ? (
                <>
                  {/* Series Selection */}
                  <div className="mb-3">
                    <label className="text-xs mr-2 text-gray-700">Show:</label>
                    <select
                      value={selectedSeries}
                      onChange={(e) => onSeriesChange(e.target.value)}
                      className="px-2 py-1 rounded border border-gray-300 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                    height={250}
                  />

                  {/* Download Button */}
                  <button
                    onClick={onDownloadCSV}
                    className="mt-3 px-3 py-1.5 bg-[#034930] text-white rounded cursor-pointer text-xs w-full hover:bg-[#023020] transition-colors"
                  >
                    Download CSV
                  </button>
                </>
              ) : chartType === "riverdepth" || chartType === "streamflow" ? (
                <GeoSFMChart
                  timeSeriesData={geoFSMTimeSeriesData}
                  dataType={chartType}
                  stationName={selectedStation?.properties?.Name || selectedStation?.properties?.Descriptio || 'GeoSFM Station'}
                  height={250}
                />
              ) : (
                <div className="text-center py-6 text-gray-600">
                  <p className="text-sm">No chart data available</p>
                </div>
              )}
            </div>
          </Box>
        </Collapse>
      </Box>
  );
};
