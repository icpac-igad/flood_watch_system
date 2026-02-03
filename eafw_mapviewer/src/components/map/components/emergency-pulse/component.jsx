import { useEffect, useRef, useCallback } from 'react';
import PropTypes from 'prop-types';

/**
 * AlertPulse Component
 * Animates the opacity of warning, alarm, and emergency icons
 * Speed depends on alert level - emergency fastest, warning slowest
 * All start in sync but emergency completes more cycles
 *
 * Cycle durations:
 * - Emergency: 800ms (fastest - most urgent)
 * - Alarm: 1200ms (medium speed)
 * - Warning: 1800ms (slower - less urgent)
 */
const AlertPulse = ({ map }) => {
  const animationRef = useRef(null);
  const iconLayerIdRef = useRef(null);
  const originalOpacityRef = useRef(0.9);
  const startTimeRef = useRef(Date.now());

  // Find the multimodal icon layer
  const findIconLayer = useCallback(() => {
    if (!map) return null;

    const style = map.getStyle();
    if (!style || !style.layers) return null;

    for (const layer of style.layers) {
      if (layer.type === 'symbol' &&
          layer.layout?.['icon-image'] &&
          (layer['source-layer']?.includes('multimodal') ||
           layer['source-layer']?.includes('public.multimodal'))) {
        return layer.id;
      }
    }

    return null;
  }, [map]);

  // Animate icons - different speeds per alert level
  const animateIcons = useCallback(() => {
    if (!map) {
      animationRef.current = requestAnimationFrame(animateIcons);
      return;
    }

    const layerId = iconLayerIdRef.current || findIconLayer();
    if (!layerId || !map.getLayer(layerId)) {
      animationRef.current = requestAnimationFrame(animateIcons);
      return;
    }

    iconLayerIdRef.current = layerId;

    // Use elapsed time from common start point for sync
    const elapsed = Date.now() - startTimeRef.current;

    // Different cycle durations - faster = more urgent
    // Emergency: 800ms cycle (fastest)
    const emergencyCycle = 800;
    const emergencyProgress = (elapsed % emergencyCycle) / emergencyCycle;
    const emergencyPulse = Math.sin(emergencyProgress * Math.PI);
    const emergencyOpacity = 0.3 + emergencyPulse * 0.7;

    // Alarm: 1200ms cycle (medium)
    const alarmCycle = 1200;
    const alarmProgress = (elapsed % alarmCycle) / alarmCycle;
    const alarmPulse = Math.sin(alarmProgress * Math.PI);
    const alarmOpacity = 0.35 + alarmPulse * 0.65;

    // Warning: 1800ms cycle (slower)
    const warningCycle = 1800;
    const warningProgress = (elapsed % warningCycle) / warningCycle;
    const warningPulse = Math.sin(warningProgress * Math.PI);
    const warningOpacity = 0.45 + warningPulse * 0.55;

    try {
      map.setPaintProperty(layerId, 'icon-opacity', [
        'match',
        ['get', 'alert_level'],
        'emergency', emergencyOpacity,
        'alarm', alarmOpacity,
        'warning', warningOpacity,
        'normal', 0.9,
        0.9
      ]);
    } catch (e) {
      // Ignore errors
    }

    animationRef.current = requestAnimationFrame(animateIcons);
  }, [map, findIconLayer]);

  useEffect(() => {
    if (!map) return;

    // Set common start time for all animations
    startTimeRef.current = Date.now();

    const startAnimation = () => {
      const layerId = findIconLayer();
      if (layerId) {
        iconLayerIdRef.current = layerId;
        try {
          const currentOpacity = map.getPaintProperty(layerId, 'icon-opacity');
          if (typeof currentOpacity === 'number') {
            originalOpacityRef.current = currentOpacity;
          }
        } catch (e) {}
      }
      animateIcons();
    };

    if (map.isStyleLoaded()) {
      startAnimation();
    } else {
      map.once('styledata', startAnimation);
    }

    const onSourceData = () => {
      if (!iconLayerIdRef.current) {
        const layerId = findIconLayer();
        if (layerId) iconLayerIdRef.current = layerId;
      }
    };
    map.on('sourcedata', onSourceData);

    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
      map.off('sourcedata', onSourceData);

      if (iconLayerIdRef.current && map.getLayer(iconLayerIdRef.current)) {
        try {
          map.setPaintProperty(iconLayerIdRef.current, 'icon-opacity', originalOpacityRef.current);
        } catch (e) {}
      }
    };
  }, [map, findIconLayer, animateIcons]);

  return null;
};

AlertPulse.propTypes = {
  map: PropTypes.object,
};

export default AlertPulse;
