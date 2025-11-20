/**
 * Custom hook for fetching and managing ensemble forecast data
 * Handles data fetching, caching, and state management for ensemble forecasts
 */

import { useState, useCallback, useEffect } from 'react';

const FASTAPI_BASE_URL = import.meta.env.VITE_FASTAPI_URL || 'http://localhost:8094/api/fast';

interface EnsembleForecast {
  date: string;
  daily_avg: string;
  daily_max: string;
  daily_min: string;
  Floodproof: string;
}

interface EnsembleFeature {
  type: 'Feature';
  geometry: {
    type: 'Point';
    coordinates: [number, number];
  };
  properties: {
    GRIDCODE: number;
    ID: number;
    Zone: number;
    x: number;
    y: number;
    admin_name: string;
    has_data: boolean;
    forecasts: EnsembleForecast[];
  };
}

interface EnsembleForecastResponse {
  type: 'FeatureCollection';
  features: EnsembleFeature[];
}

interface UseEnsembleForecastDataOptions {
  enabled: boolean;
  selectedDate: string | null;
}

interface UseEnsembleForecastDataReturn {
  data: EnsembleForecastResponse | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

// Simple in-memory cache
const ensembleCache = new Map<string, EnsembleForecastResponse>();

export const useEnsembleForecastData = ({
  enabled,
  selectedDate,
}: UseEnsembleForecastDataOptions): UseEnsembleForecastDataReturn => {
  const [data, setData] = useState<EnsembleForecastResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!enabled || !selectedDate) {
      setData(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Check cache first
      const cachedData = ensembleCache.get(selectedDate);
      if (cachedData) {
        setData(cachedData);
        setIsLoading(false);
        return;
      }

      // Fetch from API
      const url = `${FASTAPI_BASE_URL}/ensemble-forecast/${selectedDate}/`;
      const response = await fetch(url);

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error(`No ensemble forecast data available for ${selectedDate}`);
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const fetchedData: EnsembleForecastResponse = await response.json();

      // Store in cache
      ensembleCache.set(selectedDate, fetchedData);

      setData(fetchedData);
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to fetch ensemble forecast data';
      console.error('❌ Error fetching ensemble forecast data:', errorMessage);
      setError(errorMessage);
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [enabled, selectedDate]);

  // Auto-fetch when dependencies change
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
