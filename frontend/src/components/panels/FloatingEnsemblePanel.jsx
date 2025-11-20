/**
 * FloatingEnsemblePanel Component
 * A draggable, floating panel that displays ensemble forecast charts on the map
 */

import { useState, useEffect, useRef } from 'react';
import { Box, Typography, IconButton, Collapse } from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import MinimizeIcon from '@mui/icons-material/Minimize';
import MaximizeIcon from '@mui/icons-material/Maximize';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import { EnsembleForecastChart } from '../../utils/chartUtils';

export const FloatingEnsemblePanel = ({
  isVisible,
  onClose,
  selectedEnsemblePoint,
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
      const panelWidth = 480;
      const panelHeight = isMinimized ? 60 : 600;

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

  if (!isVisible || !selectedEnsemblePoint) return null;

  const props = selectedEnsemblePoint.properties;
  const hasForecastData = props?.has_data && props?.forecasts && props?.forecasts.length > 0;

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
          sm: '480px'
        },
        maxWidth: '600px',
        maxHeight: isMinimized ? 'auto' : '85vh',
        backgroundColor: '#ffffff',
        borderRadius: '8px',
        boxShadow: '0 4px 20px rgba(0,0,0,0.25)',
        border: '2px solid #9C27B0',
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
            bgcolor: '#9C27B0',
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
              Ensemble Forecast - Point #{props?.ID}
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
              maxHeight: 'calc(85vh - 50px)',
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
            {/* Point Summary */}
            <div className="bg-purple-50 rounded-lg p-3 mb-3">
              <h4 className="m-0 mb-3 text-base font-semibold text-[#6a1b9a]">
                Ensemble Control Point #{props?.ID}
              </h4>

              <div className="grid grid-cols-2 gap-2">
                <div className="flex flex-col">
                  <span className="text-xs text-gray-600 font-medium mb-1 uppercase">Grid Code</span>
                  <span className="text-sm font-semibold text-gray-900">
                    {props?.GRIDCODE || "N/A"}
                  </span>
                </div>

                <div className="flex flex-col">
                  <span className="text-xs text-gray-600 font-medium mb-1 uppercase">Zone</span>
                  <span className="text-sm font-semibold text-gray-900">
                    Zone {props?.Zone || "N/A"}
                  </span>
                </div>

                <div className="flex flex-col">
                  <span className="text-xs text-gray-600 font-medium mb-1 uppercase">Admin Region</span>
                  <span className="text-sm font-semibold text-gray-900">
                    {props?.admin_name || "N/A"}
                  </span>
                </div>

                <div className="flex flex-col">
                  <span className="text-xs text-gray-600 font-medium mb-1 uppercase">Location</span>
                  <span className="text-sm font-semibold text-gray-900">
                    {props?.y?.toFixed(4)}°, {props?.x?.toFixed(4)}°
                  </span>
                </div>

                <div className="flex flex-col col-span-2">
                  <span className="text-xs text-gray-600 font-medium mb-1 uppercase">Forecast Records</span>
                  <span className="text-sm font-semibold text-purple-700">
                    {props?.forecast_count || 0} records available
                  </span>
                </div>
              </div>
            </div>

            {/* Chart Section */}
            <div className="bg-white rounded-lg border border-purple-300 p-3 mb-3">
              <h5 className="m-0 mb-3 text-sm font-semibold text-gray-700">Ensemble Discharge Forecast</h5>

              {hasForecastData ? (
                <>
                  {/* Chart */}
                  <EnsembleForecastChart
                    forecasts={props.forecasts}
                    height={350}
                  />

                  {/* Info text */}
                  <div className="mt-3 p-2 bg-purple-50 rounded text-xs text-gray-700">
                    <strong>Note:</strong> This chart shows discharge forecasts from multiple ensemble models.
                    Each line represents a different forecasting model or scenario.
                  </div>
                </>
              ) : (
                <div className="text-center py-6 text-gray-600">
                  <p className="text-sm">No forecast data available for this ensemble point</p>
                </div>
              )}
            </div>
          </Box>
        </Collapse>
      </Box>
  );
};
