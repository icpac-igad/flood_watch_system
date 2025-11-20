import React, { useMemo, useEffect, useRef } from 'react';
import { WMSTileLayer, useMap } from 'react-leaflet';
import { WMSLayer, LayerType } from '../../types/map.types';
import { formatLayerIdWithDate, handleLayerError } from '../../utils/map/layerHelpers';

interface StableWMSLayerProps {
  url: string;
  layers: string;
  transparent?: boolean;
  format?: string;
  version?: string;
  zIndex?: number;
  layerConfig?: WMSLayer;
  selectedDate: string | null;
  layerType: LayerType;
  globalMapKey?: number;
}

export const StableWMSLayer: React.FC<StableWMSLayerProps> = ({
  url,
  layers,
  transparent = true,
  format = 'image/png',
  version = '1.1.0',
  zIndex = 100,
  layerConfig,
  selectedDate,
  layerType,
  globalMapKey = 0
}) => {
  // Return null if URL is not provided (MapServer disabled)
  if (!url || url === null) {
    return null;
  }

  const validDate = selectedDate || new Date().toISOString().split('T')[0];

  const finalLayerId = useMemo(() => {
    if (layerType === 'ibew') {
      return layers;
    }
    return layerConfig?.needsDate && validDate
      ? formatLayerIdWithDate(layers, validDate, layerType)
      : layers;
  }, [layers, layerConfig, validDate, layerType]);

  const finalUrl = useMemo(() => {
    let finalUrl = url;

    if (layerType === 'ibew' && validDate) {
      const formattedDate = validDate.replace(/-/g, '');
      const urlParams = new URLSearchParams();
      urlParams.set('date', formattedDate);
      urlParams.set('datetime', `${formattedDate}0000`);

      const separator = url.includes('?') ? '&' : '?';
      finalUrl = `${url}${separator}${urlParams.toString()}`;
    }

    const timestamp = Date.now();
    const randomId = Math.random().toString(36).substring(2, 14);
    const nanoTime = performance.now().toString().replace('.', '');
    const dateStr = validDate?.replace(/-/g, '') || 'nodate';
    const ultraCacheBuster = `cb=${timestamp}_${globalMapKey}_${dateStr}_${randomId}_${nanoTime}&nocache=${timestamp}&refresh=${globalMapKey}&_=${Date.now()}`;
    const separator = finalUrl.includes('?') ? '&' : '?';
    return `${finalUrl}${separator}${ultraCacheBuster}`;
  }, [url, layerType, validDate, globalMapKey]);

  const uniqueKey = `wms-${finalLayerId}-${validDate || 'nodate'}-${globalMapKey}`;
  const map = useMap();
  const layerRef = useRef<L.TileLayer | null>(null);

  // Force map to invalidate and redraw when date or globalMapKey changes
  useEffect(() => {
    // Force map to redraw all layers
    if (map) {
      setTimeout(() => {
        map.invalidateSize();
        // Force all tile layers to reload
        map.eachLayer((layer: any) => {
          if (layer.redraw && typeof layer.redraw === 'function') {
            layer.redraw();
          }
        });
      }, 100);
    }
  }, [validDate, globalMapKey, map, layers, finalLayerId]);

  return (
    <WMSTileLayer
      key={uniqueKey}
      url={finalUrl}
      layers={finalLayerId}
      format={format}
      transparent={transparent}
      version={version}
      updateWhenIdle={true}  // Allow updates when map is idle
      updateWhenZooming={true}  // Allow updates while zooming
      updateInterval={100}  // Update more frequently
      keepBuffer={0}  // Don't keep tiles in buffer - always fetch fresh
      maxNativeZoom={18}
      zIndex={zIndex}
      ref={layerRef as any}
      eventHandlers={{
        error: (error) => handleLayerError(finalLayerId, error),
        load: () => {}
      }}
    />
  );
};
