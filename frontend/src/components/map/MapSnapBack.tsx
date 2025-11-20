import { useEffect, useRef } from 'react';
import { useMap } from 'react-leaflet';
import { GHAView } from '../../types/map.types';

interface MapSnapBackProps {
  ghaView: GHAView;
  timeoutDuration?: number;
}

export const MapSnapBack: React.FC<MapSnapBackProps> = ({ 
  ghaView, 
  timeoutDuration = 30000 
}) => {
  const map = useMap();
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const handleMoveEnd = () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      timeoutRef.current = setTimeout(() => {
        map.setView(ghaView.center, ghaView.zoom, { animate: true, duration: 2 });
      }, timeoutDuration);
    };

    const handleMoveStart = () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };

    map.on('moveend', handleMoveEnd);
    map.on('movestart', handleMoveStart);

    return () => {
      map.off('moveend', handleMoveEnd);
      map.off('movestart', handleMoveStart);
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [map, ghaView, timeoutDuration]);

  return null;
};
