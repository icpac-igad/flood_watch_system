/**
 * Custom hook for fetching available ensemble forecast dates
 */

import { useState, useEffect } from 'react';

const FASTAPI_BASE_URL = import.meta.env.VITE_FASTAPI_URL || 'http://localhost:8094/api/fast';

interface EnsembleDateInfo {
  date: string;
  feature_count: number;
  features_with_data: number;
}

interface EnsembleDatesResponse {
  dates: EnsembleDateInfo[];
}

interface UseEnsembleForecastDatesReturn {
  dates: string[];
  isLoading: boolean;
  error: string | null;
}

export const useEnsembleForecastDates = (): UseEnsembleForecastDatesReturn => {
  const [dates, setDates] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDates = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const url = `${FASTAPI_BASE_URL}/ensemble-forecast-dates/`;
        const response = await fetch(url);

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data: EnsembleDatesResponse = await response.json();
        const dateStrings = data.dates.map(d => d.date);

        setDates(dateStrings);
      } catch (err: any) {
        const errorMessage = err.message || 'Failed to fetch ensemble forecast dates';
        console.error('❌ Error fetching ensemble forecast dates:', errorMessage);
        setError(errorMessage);
        setDates([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchDates();
  }, []);

  return {
    dates,
    isLoading,
    error
  };
};
