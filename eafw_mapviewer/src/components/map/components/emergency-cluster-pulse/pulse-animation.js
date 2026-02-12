import { PULSE_CYCLE_MS } from "./constants";
import { buildPulseRadiusExpression, buildPulseOpacityExpression } from "./pulse-filters";

export const getPulseFrameState = ({ now = Date.now(), startTime, zoom = 4 }) => {
  const elapsed = now - startTime;
  const phase = Math.sin((elapsed / PULSE_CYCLE_MS) * Math.PI * 2); // -1..+1
  const normalizedPhase = (phase + 1) / 2; // 0..1
  const zoomFactor = Math.max(0, zoom - 3);
  const minOffset = 3 + zoomFactor * 0.35;
  const maxOffset = 10 + zoomFactor * 0.65;
  const pulseOffset = minOffset + (maxOffset - minOffset) * normalizedPhase;
  const opacity = 0.24 + 0.52 * normalizedPhase; // 0.24..0.76

  return { pulseOffset, opacity };
};

export const applyPulseFrame = ({ map, pulseInfo, pulseOffset, opacity }) => {
  pulseInfo.forEach((info, pulseId) => {
    if (!map.getLayer(pulseId)) {
      pulseInfo.delete(pulseId);
      return;
    }

    try {
      map.setPaintProperty(
        pulseId,
        "circle-radius",
        buildPulseRadiusExpression(info.baseRadius, pulseOffset)
      );
      map.setPaintProperty(
        pulseId,
        "circle-opacity",
        buildPulseOpacityExpression(opacity)
      );
    } catch (e) {}
  });
};
