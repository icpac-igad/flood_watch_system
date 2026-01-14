import { useEffect, useRef, useCallback } from 'react';
import PropTypes from 'prop-types';
import { connect } from 'react-redux';

import { getInteractionSelected } from '@/components/map/selectors';

/**
 * BasinLayer Component
 * Auto-loads and displays the basin boundary when a multimodal forecast point is clicked
 * Uses hybas_id from the clicked point to fetch basin geometry from the API
 */
const BasinLayer = ({ map, selected }) => {
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

  // Watch for interaction changes to detect point clicks with hybas_id
  useEffect(() => {
    if (!map) return;

    // Clear basin when no selection
    if (!selected) {
      if (currentBasinIdRef.current) {
        removeBasinLayers();
        currentBasinIdRef.current = null;
      }
      return;
    }

    // Extract hybas_id from selected point data
    // The selected object has 'data' with merged feature properties
    const { data } = selected;
    if (!data) {
      console.log('[BasinLayer] No data in selected:', selected);
      return;
    }

    // hybas_id is directly on the data object (from MVT feature properties)
    let hybasId = data.hybas_id;

    // Debug: log data structure
    console.log('[BasinLayer] Selected data:', data);
    console.log('[BasinLayer] hybas_id:', hybasId);

    if (hybasId) {
      addBasinToMap(hybasId);
    } else {
      // If clicking a point without hybas_id, clear the basin
      if (currentBasinIdRef.current) {
        removeBasinLayers();
        currentBasinIdRef.current = null;
      }
    }
  }, [map, selected, addBasinToMap, removeBasinLayers]);

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
};

// Connect to Redux using the same selector as the popup
const mapStateToProps = (state) => ({
  selected: getInteractionSelected(state),
});

export default connect(mapStateToProps)(BasinLayer);
