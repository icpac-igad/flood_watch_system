import { EMERGENCY_COLOR, PULSE_LAYER_SUFFIX } from "./constants";
import {
  buildPulseFilter,
  normalizeRadiusExpression,
  safeJsonStringify,
  buildPulseRadiusExpression,
  buildPulseOpacityExpression,
  buildPulseBlurExpression,
} from "./pulse-filters";

export const isMultimodalCircleLayer = (layer) => {
  const sourceLayer = layer?.["source-layer"];
  return (
    (layer?.type === "circle" || layer?.type === "symbol") &&
    typeof sourceLayer === "string" &&
    sourceLayer.includes("multimodal_points")
  );
};

export const scanPulseTargets = (map) => {
  if (!map) return { targets: [], orphanPulseIds: [] };
  try {
    const style = map.getStyle();
    if (!style || !Array.isArray(style.layers)) return { targets: [], orphanPulseIds: [] };

    const targets = [];
    const existingPulseIds = [];

    style.layers.forEach((layer) => {
      const id = String(layer.id);
      if (id.includes(PULSE_LAYER_SUFFIX)) {
        existingPulseIds.push(id);
      } else if (isMultimodalCircleLayer(layer)) {
        targets.push(layer);
      }
    });

    const neededPulseIds = new Set(targets.map((t) => `${t.id}${PULSE_LAYER_SUFFIX}`));
    const orphanPulseIds = existingPulseIds.filter((id) => !neededPulseIds.has(id));

    return { targets, orphanPulseIds };
  } catch (e) {
    return { targets: [], orphanPulseIds: [] };
  }
};

export const removePulseLayer = (map, pulseInfo, layerId) => {
  try {
    if (map && map.getLayer(layerId)) map.removeLayer(layerId);
  } catch (e) {}
  pulseInfo.delete(layerId);
};

export const removeAllPulseLayers = (map, pulseInfo) => {
  try {
    const style = map?.getStyle();
    if (style?.layers) {
      style.layers.forEach((layer) => {
        if (String(layer.id).includes(PULSE_LAYER_SUFFIX)) {
          try {
            map.removeLayer(layer.id);
          } catch (e) {}
        }
      });
    }
  } catch (e) {}
  pulseInfo.clear();
};

const isTrackedPulseLayerCurrent = (tracked, { sourceLayer, source, baseFilterSig, baseRadiusSig }) =>
  !!tracked &&
  tracked.sourceLayer === sourceLayer &&
  tracked.source === source &&
  tracked.baseFilterSig === baseFilterSig &&
  tracked.baseRadiusSig === baseRadiusSig;

export const syncPulseLayers = ({ map, pulseInfo }) => {
  if (!map) return;

  const { targets, orphanPulseIds } = scanPulseTargets(map);
  orphanPulseIds.forEach((orphanId) => removePulseLayer(map, pulseInfo, orphanId));

  targets.forEach((target) => {
    const pulseId = `${target.id}${PULSE_LAYER_SUFFIX}`;
    const sourceLayer = target["source-layer"];
    const source = target.source;
    const baseFilter = target.filter || null;
    const baseRadius = normalizeRadiusExpression(target?.paint?.["circle-radius"]);
    const baseFilterSig = safeJsonStringify(baseFilter);
    const baseRadiusSig = safeJsonStringify(baseRadius);
    const tracked = pulseInfo.get(pulseId);
    const pulseExists = !!map.getLayer(pulseId);

    if (
      pulseExists &&
      isTrackedPulseLayerCurrent(tracked, { sourceLayer, source, baseFilterSig, baseRadiusSig })
    ) {
      return;
    }

    if (pulseExists) {
      removePulseLayer(map, pulseInfo, pulseId);
    }

    if (!map.getSource(source)) return;

    try {
      map.addLayer(
        {
          id: pulseId,
          type: "circle",
          source,
          "source-layer": sourceLayer,
          filter: buildPulseFilter(baseFilter),
          paint: {
            "circle-color": EMERGENCY_COLOR,
            "circle-opacity": buildPulseOpacityExpression(0.45),
            "circle-radius": buildPulseRadiusExpression(baseRadius, 5),
            "circle-blur": buildPulseBlurExpression(),
            "circle-stroke-width": 0,
          },
        },
        target.id
      );

      pulseInfo.set(pulseId, {
        baseLayerId: target.id,
        sourceLayer,
        source,
        baseRadius,
        baseFilterSig,
        baseRadiusSig,
      });
    } catch (e) {
      // map/style may still be settling; sync will retry next frame/idle
    }
  });
};
