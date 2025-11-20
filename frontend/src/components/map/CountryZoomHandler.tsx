import { useEffect } from 'react';
import { useMap } from 'react-leaflet';
import { getCountryBounds } from '../../utils/map/countryFilter';

interface CountryZoomHandlerProps {
  adminData: any;
  selectedCountry: string;
}

/**
 * CountryZoomHandler - Zooms the map to fit the selected country
 */
export const CountryZoomHandler: React.FC<CountryZoomHandlerProps> = ({
  adminData,
  selectedCountry
}) => {
  const map = useMap();

  useEffect(() => {
    if (!selectedCountry || !adminData) {
      // Reset to Greater Horn of Africa view when no country selected
      if (!selectedCountry) {
        map.setView([2.5, 40], 5);
      }
      return;
    }

    // Handle WHCA Countries - zoom to combined bounds
    if (selectedCountry === 'WHCA') {
      const whcaCountries = ['Uganda', 'Rwanda', 'South Sudan', 'Ethiopia', 'Sudan'];
      let minLat = Infinity, maxLat = -Infinity;
      let minLng = Infinity, maxLng = -Infinity;

      whcaCountries.forEach(country => {
        const bounds = getCountryBounds(adminData, country);
        if (bounds) {
          const [[south, west], [north, east]] = bounds;
          minLat = Math.min(minLat, south);
          maxLat = Math.max(maxLat, north);
          minLng = Math.min(minLng, west);
          maxLng = Math.max(maxLng, east);
        }
      });

      if (minLat !== Infinity) {
        const combinedBounds: [[number, number], [number, number]] = [
          [minLat, minLng],
          [maxLat, maxLng]
        ];

        map.fitBounds(combinedBounds, {
          padding: [50, 50],
          maxZoom: 7,
          animate: true,
          duration: 0.5
        });
        console.log('🌍 Zoomed to WHCA Countries bounds');
      }
      return;
    }

    // Single country zoom
    const bounds = getCountryBounds(adminData, selectedCountry);

    if (bounds) {
      // Fit the map to the country bounds with padding
      map.fitBounds(bounds, {
        padding: [50, 50],
        maxZoom: 8,
        animate: true,
        duration: 0.5
      });
    }
  }, [map, adminData, selectedCountry]);

  return null;
};
