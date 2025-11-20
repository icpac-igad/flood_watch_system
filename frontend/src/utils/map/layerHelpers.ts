import { LayerType } from '../../types/map.types';

/**
 * Formats layer ID with date for runtime substitution
 */
export const formatLayerIdWithDate = (
  baseLayerId: string,
  date: string | null,
  layerType: LayerType
): string => {
  if (layerType === 'ibew') {
    return baseLayerId;
  }
  
  if (!date) return baseLayerId;
  
  const formattedDate = date.replace(/-/g, '');
  
  switch(layerType) {
    case 'inundation':
    case 'impact':
      return `${baseLayerId}_${formattedDate}`;
    default:
      return baseLayerId;
  }
};

/**
 * Handles layer loading errors with appropriate logging
 */
export const handleLayerError = (layerId: string, error?: unknown): void => {
  // Error handling - silently ignore hazard layer errors
};
