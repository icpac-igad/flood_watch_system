/**
 * Custom hook for managing layer visibility state
 */

import { useState } from 'react';
import { LayerVisibility } from '../types/map.types';

export const useLayerVisibility = () => {
  const [visibility, setVisibility] = useState<LayerVisibility>({
    showMonitoringStations: true,  // Default enabled to show flood data
    showGeoFSM: false,
    showMikeHydro: false,
    showHype: false,
    showEnsemble: false
  });

  const toggleLayer = (layerName: keyof LayerVisibility) => {
    setVisibility(prev => ({
      ...prev,
      [layerName]: !prev[layerName]
    }));
  };

  const setLayerVisibility = (layerName: keyof LayerVisibility, visible: boolean) => {
    setVisibility(prev => ({
      ...prev,
      [layerName]: visible
    }));
  };

  return {
    visibility,
    toggleLayer,
    setLayerVisibility
  };
};
