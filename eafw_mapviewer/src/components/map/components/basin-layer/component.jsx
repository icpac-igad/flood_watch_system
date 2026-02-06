import { useEffect, useRef, useCallback } from 'react';
import PropTypes from 'prop-types';
import { connect } from 'react-redux';

import { getInteractionSelected, selectParamInteractions } from '@/components/map/selectors';

/**
 * BasinLayer Component
 * Displays basin boundary on the map in two scenarios:
 * 1. When a multimodal forecast point is clicked (hybas_id from point properties)
 * 2. When the watershed filter dropdown selects a basin (basin_filter + basin_id from Redux)
 */
const BasinLayer = ({ map, selected, paramInteractions }) => {
  const currentBasinIdRef = useRef(null);
  const sourceAddedRef = useRef(false);

  // Basin layer styling - make more visible
  const BASIN_FILL_COLOR = '#1E90FF';  // Dodger blue
  const BASIN_LINE_COLOR = '#0066CC';  // Darker blue
  const BASIN_FILL_OPACITY = 0.25;     // Increased from 0.15
  const BASIN_LINE_WIDTH = 3;          // Increased from 2

  // Clean up basin layers
  const removeBasinLayers = useCallback(() => {
    if (!map) return;

    try {
      if (map.getLayer('active-basin-fill')) {
        map.removeLayer('active-basin-fill');
      }
      if (map.getLayer('active-basin-line')) {
        map.removeLayer('active-basin-line');
      }
      if (map.getSource('active-basin')) {
        map.removeSource('active-basin');
      }
      sourceAddedRef.current = false;
    } catch (e) {
      // Ignore errors during cleanup
    }
  }, [map]);

  // Add basin to map
  const addBasinToMap = useCallback(async (hybasId) => {
    if (!map || !hybasId) return;

    // Don't reload if same basin
    if (currentBasinIdRef.current === hybasId) return;

    console.log('[BasinLayer] Loading basin:', hybasId);

    try {
      // Fetch basin geometry from API
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';
      const response = await fetch(`${API_BASE_URL}/api/basin/${hybasId}/`);
      if (!response.ok) {
        console.warn('[BasinLayer] Basin not found:', hybasId);
        return;
      }

      const basinFeature = await response.json();
      if (!basinFeature || !basinFeature.geometry) {
        console.warn('[BasinLayer] Invalid basin data:', hybasId);
        return;
      }

      // Remove existing basin layers
      removeBasinLayers();

      // Add new basin source
      map.addSource('active-basin', {
        type: 'geojson',
        data: basinFeature
      });
      sourceAddedRef.current = true;

      // Add fill layer on top
      map.addLayer({
        id: 'active-basin-fill',
        type: 'fill',
        source: 'active-basin',
        paint: {
          'fill-color': BASIN_FILL_COLOR,
          'fill-opacity': BASIN_FILL_OPACITY
        }
      });

      // Add line layer on top
      map.addLayer({
        id: 'active-basin-line',
        type: 'line',
        source: 'active-basin',
        paint: {
          'line-color': BASIN_LINE_COLOR,
          'line-width': BASIN_LINE_WIDTH,
          'line-dasharray': [3, 2]  // Dashed line for visibility
        }
      });

      // Fit map to basin bounds if bbox available
      if (basinFeature.bbox && basinFeature.bbox.length === 4) {
        const [minX, minY, maxX, maxY] = basinFeature.bbox;
        map.fitBounds([[minX, minY], [maxX, maxY]], {
          padding: 50,
          maxZoom: 10,
          duration: 1000
        });
      }

      currentBasinIdRef.current = hybasId;
      console.log('[BasinLayer] Basin added successfully:', hybasId, basinFeature.bbox);

    } catch (error) {
      console.error('[BasinLayer] Error loading basin:', error);
    }
  }, [map, removeBasinLayers]);

  // Watch for watershed filter changes (dropdown selection)
  useEffect(() => {
    if (!map) return;

    const basinFilter = paramInteractions?.basin_filter;
    const basinId = paramInteractions?.basin_id;

    if (basinFilter && basinId) {
      addBasinToMap(basinId);
    } else if (!basinFilter && currentBasinIdRef.current) {
      // Basin filter was cleared — only remove if no point-click basin active
      if (!selected?.data?.hybas_id) {
        removeBasinLayers();
        currentBasinIdRef.current = null;
      }
    }
  }, [map, paramInteractions?.basin_filter, paramInteractions?.basin_id, addBasinToMap, removeBasinLayers]);

  // Watch for interaction changes to detect point clicks with hybas_id
  useEffect(() => {
    if (!map) return;

    // If basin filter is active, it takes priority — don't clear on deselect
    const basinFilterActive = paramInteractions?.basin_filter && paramInteractions?.basin_id;

    // Clear basin when no selection (and no filter active)
    if (!selected) {
      if (currentBasinIdRef.current && !basinFilterActive) {
        removeBasinLayers();
        currentBasinIdRef.current = null;
      }
      return;
    }

    // Extract hybas_id from selected point data
    const { data } = selected;
    if (!data) return;

    const hybasId = data.hybas_id;

    if (hybasId) {
      addBasinToMap(hybasId);
    } else if (!basinFilterActive) {
      // If clicking a point without hybas_id and no filter active, clear the basin
      if (currentBasinIdRef.current) {
        removeBasinLayers();
        currentBasinIdRef.current = null;
      }
    }
  }, [map, selected, paramInteractions?.basin_filter, paramInteractions?.basin_id, addBasinToMap, removeBasinLayers]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      removeBasinLayers();
    };
  }, [removeBasinLayers]);

  return null;
};

BasinLayer.propTypes = {
  map: PropTypes.object,
  selected: PropTypes.object,
  paramInteractions: PropTypes.object,
};

// Connect to Redux — selected point + watershed filter state
const mapStateToProps = (state) => ({
  selected: getInteractionSelected(state),
  paramInteractions: selectParamInteractions(state),
});

export default connect(mapStateToProps)(BasinLayer);
