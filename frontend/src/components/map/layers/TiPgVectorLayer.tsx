/**
 * TiPg Vector Tiles Layer Component
 * Renders admin boundaries, rivers, and lakes from TiPg vector tiles
 * Replaces MapServer WMS layers with 90% smaller MVT tiles
 */

import { useEffect, useRef } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet.vectorgrid';

declare module 'leaflet' {
  namespace vectorGrid {
    function protobuf(url: string, options?: any): any;
  }
}

interface TiPgVectorLayerProps {
  collection: 'admin0' | 'admin1' | 'admin2' | 'rivers' | 'lakes';
  visible?: boolean;
  style?: any;
  interactive?: boolean;
  zIndex?: number;
  onFeatureClick?: (properties: any) => void;
}

const TIPG_URL = '/tipg';

// Default styles matching MapServer EXACTLY
const DEFAULT_STYLES = {
  admin0: {
    fill: true,
    fillColor: '#000000',       // Black fill
    fillOpacity: 0.0,           // Transparent fill
    color: '#000000',           // RGB(0,0,0) - black outline
    weight: 4,
    opacity: 1.0                // 100% opacity
  },
  admin1: {
    fill: true,
    fillColor: '#000000',       // Black fill
    fillOpacity: 0.0,           // Transparent fill
    color: '#505050',           // RGB(80,80,80) - gray outline
    weight: 2,
    opacity: 0.8                // 80% opacity
  },
  admin2: {
    fill: true,
    fillColor: '#000000',       // Black fill
    fillOpacity: 0.0,           // Transparent fill
    color: '#828282',           // RGB(130,130,130) - light gray outline
    weight: 1,
    opacity: 0.6                // 60% opacity
  },
  rivers: (properties: any) => {
    // Match MapServer 3-tier classification by ord_clas
    const order = properties.ord_clas || 1;

    if (order >= 6) {
      // Order 6+: Largest rivers (white/almost invisible)
      return {
        color: '#f5faff',       // RGB(245,250,255) - very light blue/white
        weight: 1.2,
        opacity: 0.20           // 20% opacity
      };
    } else if (order >= 4) {
      // Order 4-5: Large tributaries (semi-white)
      return {
        color: '#dcebf5',       // RGB(220,235,245) - semi-white
        weight: 0.8,
        opacity: 0.25           // 25% opacity
      };
    } else {
      // Order 1-3: Small rivers (DARK BLUE)
      return {
        color: '#1e5aa0',       // RGB(30,90,160) - dark blue
        weight: 0.5,
        opacity: 0.35           // 35% opacity
      };
    }
  },
  lakes: {
    fill: true,
    fillColor: '#55a0d2',       // RGB(85,160,210) - blue
    fillOpacity: 1.0,           // 100% opacity (opaque like MapServer)
    color: '#55a0d2',           // RGB(85,160,210) - same blue outline
    weight: 1,
    opacity: 1.0                // 100% opacity
  }
};

// Collection ID mapping (tables in pgstac schema)
const COLLECTION_IDS = {
  admin0: 'pgstac.Impact_admin0',
  admin1: 'pgstac.Impact_admin1',
  admin2: 'pgstac.Impact_admin2',
  rivers: 'pgstac.Impact_hydrorivers',
  lakes: 'pgstac.Impact_waterbodies'
};

export const TiPgVectorLayer: React.FC<TiPgVectorLayerProps> = ({
  collection,
  visible = true,
  style,
  interactive = false,
  zIndex,
  onFeatureClick
}) => {
  const map = useMap();
  const layerRef = useRef<any>(null);

  useEffect(() => {
    if (!map || !visible) {
      if (layerRef.current) {
        map.removeLayer(layerRef.current);
        layerRef.current = null;
      }
      return;
    }

    // Build tile URL (using WebMercatorQuad for standard web maps)
    const collectionId = COLLECTION_IDS[collection];
    const tileUrl = `${TIPG_URL}/collections/${collectionId}/tiles/WebMercatorQuad/{z}/{x}/{y}`;

    // Get style for this layer
    const layerStyle = style || DEFAULT_STYLES[collection];

    // Create vector tile layer
    const vectorTileOptions: any = {
      rendererFactory: (L.canvas as any).tile,
      interactive,
      pane: 'overlayPane',  // Render above tile layers (basemaps)
      vectorTileLayerStyles: {
        'default': layerStyle  // TiPg uses 'default' as the layer name in vector tiles
      },
      getFeatureId: (f: any) => f.properties.id
    };

    // Set z-index if provided to maintain consistent layer ordering
    if (zIndex !== undefined) {
      vectorTileOptions.zIndex = zIndex;
    }

    // Add click handler if provided
    if (interactive && onFeatureClick) {
      vectorTileOptions.interactive = true;
    }

    layerRef.current = (L.vectorGrid as any).protobuf(tileUrl, vectorTileOptions);

    // Add click event if needed
    if (interactive && onFeatureClick) {
      layerRef.current.on('click', (e: any) => {
        if (e.layer && e.layer.properties) {
          onFeatureClick(e.layer.properties);
        }
      });
    }

    layerRef.current.addTo(map);

    return () => {
      if (layerRef.current) {
        map.removeLayer(layerRef.current);
        layerRef.current = null;
      }
    };
  }, [map, collection, visible, style, interactive, zIndex, onFeatureClick]);

  return null;
};
