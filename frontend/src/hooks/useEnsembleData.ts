/**
 * Custom hook for fetching ensemble control points data
 */

import { useState, useEffect, useCallback } from 'react';
import { API_ENDPOINTS } from '../config/endpoints';

interface ForecastRecord {
  date: string;
  Floodproof?: string;
  GeoSFM?: string;
  daily_avg?: string;
  daily_max?: string;
  daily_min?: string;
  Mike_Hydro_RFE?: string;
  Mike_Hydro_CHIRP?: string;
  Mike_Hydro_IMERG?: string;
}

interface EnsembleFeature {
  type: 'Feature';
  properties: {
    ID: number;
    admin_name: string | null;
    x: number;
    y: number;
    Zone: number;
    GRIDCODE: number;
    Node: boolean;
    has_data?: boolean;
    forecasts?: ForecastRecord[];
    forecast_count?: number;
  };
  geometry: {
    type: 'Point';
    coordinates: [number, number];
  };
}

interface EnsembleData {
  type: 'FeatureCollection';
  features: EnsembleFeature[];
}

interface UseEnsembleDataOptions {
  enabled: boolean;
  selectedDate?: string | null;
}

interface UseEnsembleDataReturn {
  data: EnsembleData | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

// Simple in-memory cache
const ensembleCache = new Map<string, EnsembleData>();

export const useEnsembleData = ({
  enabled,
  selectedDate
}: UseEnsembleDataOptions): UseEnsembleDataReturn => {
  const [data, setData] = useState<EnsembleData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!enabled) {
      setData(null);
      return;
    }

    // Build endpoint URL based on whether date is provided
    const endpoint = selectedDate
      ? `${API_ENDPOINTS.forecasts.ensemble.replace('/ensemble-control-points', '')}/ensemble-forecast/${selectedDate}/`
      : API_ENDPOINTS.forecasts.ensemble;

    // TEMPORARILY DISABLED: Skip cache to debug data issues
    // if (selectedDate) {
    //   const cachedData = ensembleCache.get(selectedDate);
    //   if (cachedData) {
    //     console.log('✅ Using cached ensemble data for', selectedDate);
    //     setData(cachedData);
    //     return;
    //   }
    // }

    setIsLoading(true);
    setError(null);

    try {
      // Fetch ensemble points from FastAPI
      // Add cache-busting to force fresh data
      const cacheBuster = `?_=${Date.now()}`;
      const response = await fetch(endpoint + cacheBuster, {
        cache: 'no-store',
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache'
        }
      });

      if (!response.ok) {
        if (response.status === 404) {
          setData(null);
          return;
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      let geojsonData: any = await response.json();

      // Check if the response is a string that needs to be parsed
      if (typeof geojsonData === 'string') {
        geojsonData = JSON.parse(geojsonData);
      }

      // The endpoint now returns complete GeoJSON with embedded forecast data
      // No transformation needed - just set it directly
      const ensembleData = geojsonData as EnsembleData;

      // Cache the data if date is specified
      if (selectedDate) {
        ensembleCache.set(selectedDate, ensembleData);
      }

      setData(ensembleData);
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to fetch ensemble control points';
      setError(errorMessage);
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [enabled, selectedDate]);

  // Auto-fetch when enabled changes
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    data,
    isLoading,
    error,
    refetch: fetchData
  };
};
