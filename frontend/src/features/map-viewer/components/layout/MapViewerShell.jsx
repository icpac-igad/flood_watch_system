import { useEffect } from 'react';
import { Box } from '@mui/material';
import { MapViewerProvider, useMapUI } from '../../context/MapViewerContext';
import { injectMarkerAnimations } from '../../config/animationStyles';
import { MuiSidebar } from '../../../../components/layout/MuiSidebar';
import MapViewer from '../../../../components/pages/MapViewer';

/**
 * MapViewerShell - Main orchestrator for the Map Viewer feature
 * 
 * This component composes the main layout with sidebar, map, and panels.
 * Uses MapViewerContext for centralized state management.
 * 
 * Layout Structure:
 * ┌──────────────────────────────────────┐
 * │  Sidebar  │  Map Canvas + Panels     │
 * └──────────────────────────────────────┘
 */
function MapViewerContent() {
  const { ui, toggleSidebar } = useMapUI();

  return (
    <Box
      sx={{
        width: '100%',
        height: 'calc(100vh - 64px)', // Full height minus navbar
        display: 'flex',
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      {/* Left Sidebar - Layer Controls & Filters */}
      <MuiSidebar
        isOpen={ui.isSidebarActive}
        onToggle={toggleSidebar}
      >
        {/* Temporary: Will be replaced with extracted sidebar components */}
        <Box sx={{ p: 2, color: 'text.secondary' }}>
          Sidebar content (to be extracted)
        </Box>
      </MuiSidebar>

      {/* Main Map Area + Overlays */}
      <Box
        sx={{
          flex: 1,
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* 
          TEMPORARY: Using existing MapViewer for map rendering
          This will be replaced with:
          - MapCanvas (Leaflet map with layers)
          - ForecastChartsPanel (bottom chart panel)
          - StationDetailsPanel (right panel)
          - MetadataModal
          - AlertLegend
        */}
        <MapViewer />
      </Box>
    </Box>
  );
}

/**
 * MapViewerShell with Provider
 * Wraps the content with context and initializes animations
 */
export function MapViewerShell() {
  // Initialize marker animations once on mount
  useEffect(() => {
    injectMarkerAnimations();
  }, []);

  return (
    <MapViewerProvider>
      <MapViewerContent />
    </MapViewerProvider>
  );
}

export default MapViewerShell;
