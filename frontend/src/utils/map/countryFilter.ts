/**
 * Country filtering utilities for FloodWatch
 * Supports both direct GeoJSON loading and MapServer WMS (future)
 */

interface CountryOption {
  code: string;
  name: string;
  value: string;
}

interface GeoJSONFeature {
  type: string;
  geometry: {
    type: string;
    coordinates: any;
  };
  properties: {
    ADM0_NAME?: string;
    ADMIN?: string;
    country?: string;
    [key: string]: any;
  };
}

interface GeoJSONData {
  type: string;
  features: GeoJSONFeature[];
}

/**
 * East African countries in the FloodWatch system
 */
export const EAST_AFRICAN_COUNTRIES: CountryOption[] = [
  { code: 'ALL', name: 'All Countries', value: '' },
  { code: 'BI', name: 'Burundi', value: 'Burundi' },
  { code: 'DJ', name: 'Djibouti', value: 'Djibouti' },
  { code: 'ER', name: 'Eritrea', value: 'Eritrea' },
  { code: 'ET', name: 'Ethiopia', value: 'Ethiopia' },
  { code: 'KE', name: 'Kenya', value: 'Kenya' },
  { code: 'RW', name: 'Rwanda', value: 'Rwanda' },
  { code: 'SO', name: 'Somalia', value: 'Somalia' },
  { code: 'SS', name: 'South Sudan', value: 'South Sudan' },
  { code: 'SD', name: 'Sudan', value: 'Sudan' },
  { code: 'TZ', name: 'Tanzania', value: 'Tanzania' },
  { code: 'UG', name: 'Uganda', value: 'Uganda' },
];

/**
 * Extract unique countries from Admin0 GeoJSON data
 * @param adminData - GeoJSON admin boundary data (Admin0 = country level)
 * @returns Array of country objects with code and name
 */
export const extractCountriesFromAdminData = (adminData: GeoJSONData | null): CountryOption[] => {
  if (!adminData?.features) return EAST_AFRICAN_COUNTRIES;

  const countries = new Set<string>();
  adminData.features.forEach(feature => {
    // Check multiple possible property names for country
    // Admin0 model uses 'country' field
    const countryName = feature.properties?.country ||
                       feature.properties?.ADM0_NAME ||
                       feature.properties?.ADMIN;
    if (countryName && countryName !== 'None') {
      countries.add(countryName);
    }
  });

  // If no countries found, return default list
  if (countries.size === 0) return EAST_AFRICAN_COUNTRIES;

  const countryList: CountryOption[] = [{ code: 'ALL', name: 'All Countries', value: '' }];
  Array.from(countries).sort().forEach((country: string) => {
    const countryCode = country.substring(0, 2).toUpperCase();
    countryList.push({ code: countryCode, name: country, value: country });
  });

  return countryList;
};

/**
 * Filter GeoJSON features by country
 * @param geojsonData - GeoJSON data to filter
 * @param country - Country name to filter by
 * @returns Filtered GeoJSON
 */
export const filterGeoJSONByCountry = (geojsonData: GeoJSONData | null, country: string): GeoJSONData | null => {
  if (!country || !geojsonData?.features) return geojsonData;
  
  return {
    ...geojsonData,
    features: geojsonData.features.filter(
      feature => feature.properties?.ADM0_NAME === country || 
                 feature.properties?.ADMIN === country ||
                 feature.properties?.country === country
    )
  };
};

/**
 * Get bounding box for a country from Admin0 data
 * @param adminData - Admin0 GeoJSON data (country boundaries)
 * @param country - Country name
 * @returns [[south, west], [north, east]] or null
 */
export const getCountryBounds = (adminData: GeoJSONData | null, country: string): [[number, number], [number, number]] | null => {
  if (!country || !adminData?.features) return null;

  const countryFeatures = adminData.features.filter(
    feature => feature.properties?.country === country ||
               feature.properties?.ADM0_NAME === country
  );
  
  if (countryFeatures.length === 0) return null;
  
  let minLat = Infinity, maxLat = -Infinity;
  let minLng = Infinity, maxLng = -Infinity;
  
  countryFeatures.forEach(feature => {
    if (feature.geometry?.type === 'Polygon') {
      feature.geometry.coordinates[0].forEach((coord: number[]) => {
        const [lng, lat] = coord;
        minLng = Math.min(minLng, lng);
        maxLng = Math.max(maxLng, lng);
        minLat = Math.min(minLat, lat);
        maxLat = Math.max(maxLat, lat);
      });
    } else if (feature.geometry?.type === 'MultiPolygon') {
      feature.geometry.coordinates.forEach((polygon: number[][][]) => {
        polygon[0].forEach((coord: number[]) => {
          const [lng, lat] = coord;
          minLng = Math.min(minLng, lng);
          maxLng = Math.max(maxLng, lng);
          minLat = Math.min(minLat, lat);
          maxLat = Math.max(maxLat, lat);
        });
      });
    }
  });
  
  if (minLat === Infinity) return null;
  
  return [
    [minLat, minLng],
    [maxLat, maxLng]
  ];
};

/**
 * Get country geometry for clipping/masking
 * @param adminData - Admin0 GeoJSON data (country boundaries)
 * @param country - Country name
 * @returns GeoJSON geometry or null
 */
export const getCountryGeometry = (adminData: GeoJSONData | null, country: string): any | null => {
  if (!country || !adminData?.features) return null;

  const countryFeatures = adminData.features.filter(
    feature => feature.properties?.country === country ||
               feature.properties?.ADM0_NAME === country
  );
  
  if (countryFeatures.length === 0) return null;
  
  // If single feature, return its geometry
  if (countryFeatures.length === 1) {
    return countryFeatures[0].geometry;
  }
  
  // If multiple features, combine into MultiPolygon
  const polygons: number[][][][] = [];
  countryFeatures.forEach(feature => {
    if (feature.geometry?.type === 'Polygon') {
      polygons.push(feature.geometry.coordinates);
    } else if (feature.geometry?.type === 'MultiPolygon') {
      polygons.push(...feature.geometry.coordinates);
    }
  });
  
  return {
    type: 'MultiPolygon',
    coordinates: polygons
  };
};

/**
 * Create inverse mask geometry (world minus country)
 * This creates a polygon that covers the entire world except the selected country
 * @param adminData - Admin1 GeoJSON data
 * @param country - Country name
 * @returns Inverse mask GeoJSON or null
 */
export const createCountryInverseMask = (adminData: GeoJSONData | null, country: string): any | null => {
  if (!country || !adminData?.features) return null;
  
  const countryGeometry = getCountryGeometry(adminData, country);
  if (!countryGeometry) return null;
  
  // This will be used with Leaflet's mask functionality
  return {
    type: 'Feature',
    properties: { mask: true },
    geometry: countryGeometry
  };
};

/**
 * Get MapServer WMS CQL filter for country (future use)
 * @param country - Country name
 * @returns CQL filter string
 */
export const getCountryWMSFilter = (country: string): string => {
  if (!country) return '';
  return `ADM0_NAME='${country}'`;
};

/**
 * Point-in-polygon algorithm using ray casting
 * @param point - [lng, lat] point to test
 * @param polygon - Array of [lng, lat] coordinates defining the polygon
 * @returns true if point is inside polygon
 */
const pointInPolygon = (point: [number, number], polygon: [number, number][]): boolean => {
  const [x, y] = point;
  let inside = false;

  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [xi, yi] = polygon[i];
    const [xj, yj] = polygon[j];

    const intersect = ((yi > y) !== (yj > y)) &&
      (x < (xj - xi) * (y - yi) / (yj - yi) + xi);

    if (intersect) inside = !inside;
  }

  return inside;
};

/**
 * Check if a point is inside any polygon of a geometry
 * @param point - [lng, lat] point to test
 * @param geometry - GeoJSON geometry (Polygon or MultiPolygon)
 * @returns true if point is inside geometry
 */
const pointInGeometry = (point: [number, number], geometry: any): boolean => {
  if (!geometry) return false;

  if (geometry.type === 'Polygon') {
    // Check if point is in outer ring
    const outerRing = geometry.coordinates[0];
    if (!pointInPolygon(point, outerRing)) return false;

    // Check if point is in any hole (if so, it's outside)
    for (let i = 1; i < geometry.coordinates.length; i++) {
      if (pointInPolygon(point, geometry.coordinates[i])) return false;
    }

    return true;
  } else if (geometry.type === 'MultiPolygon') {
    // Check each polygon in multipolygon
    for (const polygon of geometry.coordinates) {
      const outerRing = polygon[0];
      let inPolygon = pointInPolygon(point, outerRing);

      if (inPolygon) {
        // Check holes
        for (let i = 1; i < polygon.length; i++) {
          if (pointInPolygon(point, polygon[i])) {
            inPolygon = false;
            break;
          }
        }
        if (inPolygon) return true;
      }
    }
  }

  return false;
};

/**
 * Filter point features by country using spatial intersection
 * @param geojsonData - GeoJSON data with Point features
 * @param adminData - Admin boundary data
 * @param country - Country name to filter by
 * @returns Filtered GeoJSON
 */
export const filterPointsByCountry = (
  geojsonData: GeoJSONData | null,
  adminData: GeoJSONData | null,
  country: string
): GeoJSONData | null => {
  if (!country || !geojsonData?.features || !adminData?.features) return geojsonData;

  const countryGeometry = getCountryGeometry(adminData, country);
  if (!countryGeometry) return geojsonData;

  return {
    ...geojsonData,
    features: geojsonData.features.filter(feature => {
      if (feature.geometry?.type === 'Point') {
        const [lng, lat] = feature.geometry.coordinates;
        return pointInGeometry([lng, lat], countryGeometry);
      }
      return false; // Non-point features are excluded
    })
  };
};

/**
 * Configuration for country filtering data source
 */
export const COUNTRY_FILTER_CONFIG = {
  // Set to 'geojson' for direct loading, 'wms' for MapServer
  dataSource: 'geojson' as 'geojson' | 'wms',
  
  // GeoJSON file path (used when dataSource is 'geojson')
  geojsonPath: '/Admin1.geojson',
  
  // MapServer WMS layer name (used when dataSource is 'wms')
  wmsLayer: 'admin1_boundaries',
  
  // Property name containing country in GeoJSON
  countryProperty: 'ADM0_NAME',
};
