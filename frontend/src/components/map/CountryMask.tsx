import { useEffect } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import { getCountryGeometry } from '../../utils/map/countryFilter';

interface CountryMaskProps {
  adminData: any;
  selectedCountry: string;
}

/**
 * CountryMask component - Creates a visual mask to clip the map to a selected country
 * This creates an overlay that dims everything except the selected country
 */
export const CountryMask: React.FC<CountryMaskProps> = ({ adminData, selectedCountry }) => {
  const map = useMap();

  useEffect(() => {
    if (!selectedCountry || !adminData) {
      // Remove any existing mask
      map.eachLayer((layer: any) => {
        if (layer.options?.pane === 'countryMask') {
          map.removeLayer(layer);
        }
      });
      return;
    }

    // Create a custom pane for the mask if it doesn't exist
    if (!map.getPane('countryMask')) {
      const pane = map.createPane('countryMask');
      pane.style.zIndex = '600'; // Above base map (400) but below overlays (650)
    }

    // Create world rectangle (covers entire world)
    const worldBounds: [number, number][][] = [[
      [-90, -180],
      [90, -180],
      [90, 180],
      [-90, 180],
      [-90, -180]
    ]];

    // Extract country coordinates to create holes in the world polygon
    let countryCoords: [number, number][][] = [];

    // Handle WHCA Countries - create holes for all 5 countries
    if (selectedCountry === 'WHCA') {
      const whcaCountries = ['Uganda', 'Rwanda', 'South Sudan', 'Ethiopia', 'Sudan'];

      whcaCountries.forEach(country => {
        const countryGeometry = getCountryGeometry(adminData, country);
        if (!countryGeometry) return;

        if (countryGeometry.type === 'Polygon') {
          countryGeometry.coordinates.forEach((ring: number[][]) => {
            countryCoords.push(
              ring.map(coord => [coord[1], coord[0]] as [number, number])
            );
          });
        } else if (countryGeometry.type === 'MultiPolygon') {
          countryGeometry.coordinates.forEach((polygon: number[][][]) => {
            polygon.forEach((ring: number[][]) => {
              countryCoords.push(
                ring.map(coord => [coord[1], coord[0]] as [number, number])
              );
            });
          });
        }
      });

      console.log('🌍 Creating mask for WHCA Countries with', countryCoords.length, 'holes');
    } else {
      // Single country mask
      const countryGeometry = getCountryGeometry(adminData, selectedCountry);
      if (!countryGeometry) return;

      if (countryGeometry.type === 'Polygon') {
        countryCoords = countryGeometry.coordinates.map((ring: number[][]) =>
          ring.map(coord => [coord[1], coord[0]] as [number, number])
        );
      } else if (countryGeometry.type === 'MultiPolygon') {
        countryGeometry.coordinates.forEach((polygon: number[][][]) => {
          polygon.forEach((ring: number[][]) => {
            countryCoords.push(
              ring.map(coord => [coord[1], coord[0]] as [number, number])
            );
          });
        });
      }
    }

    // Create polygon with holes (world minus country/countries)
    // Leaflet supports polygon holes by adding additional coordinate arrays
    const maskCoords = [worldBounds[0], ...countryCoords];

    // Remove existing mask layers
    map.eachLayer((layer: any) => {
      if (layer.options?.pane === 'countryMask') {
        map.removeLayer(layer);
      }
    });

    // Create the mask polygon
    const maskLayer = L.polygon(maskCoords, {
      pane: 'countryMask',
      color: '#000',
      fillColor: '#000',
      fillOpacity: 0.5,
      weight: 0,
      interactive: false,
    });

    maskLayer.addTo(map);

    // Cleanup on unmount or when country changes
    return () => {
      map.removeLayer(maskLayer);
    };
  }, [map, adminData, selectedCountry]);

  return null;
};
