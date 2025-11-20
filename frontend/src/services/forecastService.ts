/**
 * Custom hook for fetching and managing forecast data
 * Handles data fetching, caching, and state management for monitoring stations
 */

import { useState, useCallback, useEffect } from 'react';
import { forecastCache } from './cacheService';
import { ForecastDataResponse } from '../types/map.types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8094/api';

interface UseForecastDataOptions {
  enabled: boolean;
  selectedDate: string | null;
  selectedCountry: string | null;
  availableDates: string[];
}

interface UseForecastDataReturn {
  data: ForecastDataResponse | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export const useForecastData = ({
  enabled,
  selectedDate,
  selectedCountry,
  availableDates
}: UseForecastDataOptions): UseForecastDataReturn => {
  const [data, setData] = useState<ForecastDataResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!enabled) {
      setData(null);
      return;
    }

    // Use server-provided dates, never default to today
    const requestedDate = selectedDate || availableDates[0];
    if (!requestedDate) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Check cache first for instant loading
      const cachedData = forecastCache.get(requestedDate, selectedCountry);
      if (cachedData) {
        setData(cachedData);
        setIsLoading(false);
        return;
      }

      // Build URL with country filter if applicable
      const baseUrl = `${API_BASE_URL}/fast/merged-forecast/${requestedDate}/`;
      const url = selectedCountry
        ? `${baseUrl}?country=${encodeURIComponent(selectedCountry)}`
        : baseUrl;

      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const fetchedData: ForecastDataResponse = await response.json();

      // Store in cache for instant future access
      forecastCache.set(requestedDate, selectedCountry, fetchedData);

      setData(fetchedData);
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to fetch forecast data';
      console.error('❌ Error fetching forecast data:', errorMessage);
      setError(errorMessage);
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [enabled, selectedDate, selectedCountry, availableDates]);

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
