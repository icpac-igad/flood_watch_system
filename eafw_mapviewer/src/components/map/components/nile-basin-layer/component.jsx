import { useEffect, useRef, useCallback } from 'react';
import PropTypes from 'prop-types';
import { connect } from 'react-redux';

import { selectParamInteractions } from '@/components/map/selectors';
import nileBasinData from '@/assets/data/nile-basin.json';

const NILE_SOURCE_ID = 'nile-basin';
const NILE_LINE_LAYER_ID = 'nile-basin-line';

const NileBasinLayer = ({ map, paramInteractions }) => {
  const addedRef = useRef(false);

  const removeLayer = useCallback(() => {
    if (!map) return;
    try {
      if (map.getLayer(NILE_LINE_LAYER_ID)) map.removeLayer(NILE_LINE_LAYER_ID);
      if (map.getSource(NILE_SOURCE_ID)) map.removeSource(NILE_SOURCE_ID);
      addedRef.current = false;
    } catch (e) {
      // Ignore cleanup errors
    }
  }, [map]);

  const addLayer = useCallback(() => {
    if (!map || addedRef.current) return;

    removeLayer();

    map.addSource(NILE_SOURCE_ID, {
      type: 'geojson',
      data: nileBasinData,
    });

    // Find the topmost layer to ensure the Nile line renders above everything
    const layers = map.getStyle()?.layers;
    const topLayerId = layers && layers.length > 0
      ? layers[layers.length - 1].id
      : undefined;

    map.addLayer(
      {
        id: NILE_LINE_LAYER_ID,
        type: 'line',
        source: NILE_SOURCE_ID,
        paint: {
          'line-color': '#333333',
          'line-width': 3,
          'line-dasharray': [6, 4],
          'line-opacity': 0.9,
        },
      },
    );

    // Move to top after adding
    if (topLayerId && map.getLayer(NILE_LINE_LAYER_ID)) {
      try {
        map.moveLayer(NILE_LINE_LAYER_ID);
      } catch (e) {
        // Ignore if move fails
      }
    }

    addedRef.current = true;
  }, [map, removeLayer]);

  // Re-raise layer to top when other layers are added/changed
  useEffect(() => {
    if (!map || !addedRef.current) return;

    const raiseToTop = () => {
      if (map.getLayer(NILE_LINE_LAYER_ID)) {
        try {
          map.moveLayer(NILE_LINE_LAYER_ID);
        } catch (e) {
          // Ignore
        }
      }
    };

    map.on('styledata', raiseToTop);
    return () => {
      map.off('styledata', raiseToTop);
    };
  }, [map, addedRef.current]);

  useEffect(() => {
    if (!map) return;

    const isWhcaActive =
      paramInteractions?.whca_filter === true ||
      paramInteractions?.whca_filter === 'true';

    if (isWhcaActive) {
      addLayer();
    } else if (addedRef.current) {
      removeLayer();
    }
  }, [map, paramInteractions?.whca_filter, addLayer, removeLayer]);

  useEffect(() => {
    return () => removeLayer();
  }, [removeLayer]);

  return null;
};

NileBasinLayer.propTypes = {
  map: PropTypes.object,
  paramInteractions: PropTypes.object,
};

const mapStateToProps = (state) => ({
  paramInteractions: selectParamInteractions(state),
});

export default connect(mapStateToProps)(NileBasinLayer);
