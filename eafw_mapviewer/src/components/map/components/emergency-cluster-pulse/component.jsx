import { useCallback, useEffect, useRef } from "react";
import PropTypes from "prop-types";
import { PULSE_LAYER_SUFFIX } from "./constants";
import { syncPulseLayers, removeAllPulseLayers } from "./pulse-targets";
import { getPulseFrameState, applyPulseFrame } from "./pulse-animation";

/**
 * EmergencyClusterPulse
 *
 * Adds a soft breathing GLOW around ALL emergency points/clusters.
 * Uses a filled circle with high blur to create a diffused radiating aura
 * that smoothly expands and contracts (sine wave) — like an active event.
 *
 * Only the pulse overlay layers are animated; base layers are never touched.
 */
const EmergencyClusterPulse = ({ map }) => {
  const animationRef = useRef(null);
  const startTimeRef = useRef(Date.now());
  const interceptInstalledRef = useRef(false);

  // Track pulse layers: Map<pulseLayerId, { baseLayerId, sourceLayer, source, baseRadius }>
  const pulseInfoRef = useRef(new Map());

  const ensurePulseLayers = useCallback(() => {
    if (!map) return;
    syncPulseLayers({ map, pulseInfo: pulseInfoRef.current });
  }, [map]);

  const animate = useCallback(() => {
    if (!map) {
      animationRef.current = requestAnimationFrame(animate);
      return;
    }

    ensurePulseLayers();

    const pulseFrame = getPulseFrameState({
      startTime: startTimeRef.current,
      zoom: typeof map.getZoom === "function" ? map.getZoom() : 4,
    });
    applyPulseFrame({
      map,
      pulseInfo: pulseInfoRef.current,
      pulseOffset: pulseFrame.pulseOffset,
      opacity: pulseFrame.opacity,
    });

    animationRef.current = requestAnimationFrame(animate);
  }, [map, ensurePulseLayers]);

  // Intercept map.removeSource so pulse layers that depend on the source
  // are removed first, preventing "Source cannot be removed while layer is
  // using it" errors when the layer-manager swaps tile URLs.
  useEffect(() => {
    if (!map || interceptInstalledRef.current) return;
    interceptInstalledRef.current = true;

    const originalRemoveSource = map.removeSource.bind(map);
    map.removeSource = function (sourceId) {
      try {
        const style = map.getStyle();
        if (style?.layers) {
          style.layers.forEach((layer) => {
            if (
              layer.source === sourceId &&
              String(layer.id).includes(PULSE_LAYER_SUFFIX)
            ) {
              try {
                map.removeLayer(layer.id);
              } catch (_e) {
                /* already removed */
              }
            }
          });
        }
      } catch (_e) {
        /* style not ready */
      }
      // Also clear our tracking for any pulse layers that used this source
      pulseInfoRef.current.forEach((info, pulseId) => {
        if (info.source === sourceId) pulseInfoRef.current.delete(pulseId);
      });
      return originalRemoveSource(sourceId);
    };

    return () => {
      map.removeSource = originalRemoveSource;
      interceptInstalledRef.current = false;
    };
  }, [map]);

  useEffect(() => {
    if (!map) return;

    const pulseInfo = pulseInfoRef.current;
    startTimeRef.current = Date.now();
    pulseInfo.clear();

    const start = () => {
      if (!animationRef.current) {
        animationRef.current = requestAnimationFrame(animate);
      }
    };

    // Also re-sync pulse layers after map settles (filter/source changes)
    const onIdle = () => ensurePulseLayers();

    if (map.isStyleLoaded()) {
      start();
    } else {
      map.once("styledata", start);
    }

    map.on("idle", onIdle);

    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
      map.off("idle", onIdle);

      removeAllPulseLayers(map, pulseInfo);
    };
  }, [map, animate, ensurePulseLayers]);

  return null;
};

EmergencyClusterPulse.propTypes = {
  map: PropTypes.object,
};

export default EmergencyClusterPulse;
