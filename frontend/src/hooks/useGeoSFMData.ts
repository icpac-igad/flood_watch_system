/**
 * Custom hook for fetching GeoSFM forecast data
 */

import { useState, useCallback, useEffect } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8094/api';

interface GeoSFMFeature {
  type: 'Feature';
  properties: any;
  geometry: any;
}

interface GeoSFMData {
  type: 'FeatureCollection';
  features: GeoSFMFeature[];
}

interface AvailableDatesResponse {
  dates: string[];
  detailed_dates: Array<{ date: string; count: number }>;
  count: number;
  latest: string | null;
}

interface UseGeoSFMDataOptions {
  enabled: boolean;
  selectedDate: string | null;
}

interface UseGeoSFMDataReturn {
  data: GeoSFMData | null;
  availableDates: string[];
  latestDate: string | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export const useGeoSFMData = ({
  enabled,
  selectedDate
}: UseGeoSFMDataOptions): UseGeoSFMDataReturn => {
  const [data, setData] = useState<GeoSFMData | null>(null);
  const [availableDates, setAvailableDates] = useState<string[]>([]);
  const [latestDate, setLatestDate] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch available dates
  useEffect(() => {
    const fetchAvailableDates = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/geosfm/available-dates/`);

        if (response.ok) {
          const data: AvailableDatesResponse = await response.json();
          setAvailableDates(data.dates || []);
          setLatestDate(data.latest || (data.dates?.[0] ?? null));
        } else if (response.status === 404) {
          // GeoSFM data not available, return empty
          setAvailableDates([]);
          setLatestDate(null);
        }
      } catch (err: any) {
        console.error('❌ Error fetching GeoSFM available dates:', err.message);
      }
    };

    if (enabled) {
      fetchAvailableDates();
    }
  }, [enabled]);

  // Fetch GeoSFM data for selected date
  const fetchData = useCallback(async () => {
    if (!enabled) {
      setData(null);
      return;
    }

    const requestedDate = selectedDate || latestDate;
    if (!requestedDate) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/geosfm/geojson/${requestedDate}/`);

      if (!response.ok) {
        if (response.status === 404) {
          setData(null);
          return;
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const fetchedData: GeoSFMData = await response.json();

      setData(fetchedData);
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to fetch GeoSFM data';
      console.error('❌ Error fetching GeoSFM data:', errorMessage);
      setError(errorMessage);
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [enabled, selectedDate, latestDate]);

  // Auto-fetch when dependencies change
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    data,
    availableDates,
    latestDate,
    isLoading,
    error,
    refetch: fetchData
  };
};
