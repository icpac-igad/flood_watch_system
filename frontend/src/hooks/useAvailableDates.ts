/**
 * Custom hook for fetching available forecast dates
 */

import { useState, useEffect } from 'react';
import { AvailableDatesResponse } from '../types/map.types';

const FASTAPI_BASE_URL = import.meta.env.VITE_FASTAPI_URL || 'http://localhost:8094/api/fast';

interface UseAvailableDatesReturn {
  dates: string[];
  latestDate: string | null;
  isLoading: boolean;
  error: string | null;
}

export const useAvailableDates = (): UseAvailableDatesReturn => {
  const [dates, setDates] = useState<string[]>([]);
  const [latestDate, setLatestDate] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAvailableDates = async () => {
      try {
        const response = await fetch(`${FASTAPI_BASE_URL}/merged-forecast/dates/`);

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data: AvailableDatesResponse = await response.json();

        setDates(data.dates || []);
        setLatestDate(data.latest || (data.dates?.[0] ?? null));
      } catch (err: any) {
        console.error('❌ Error fetching available dates:', err.message);
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };

    fetchAvailableDates();
  }, []);

  return {
    dates,
    latestDate,
    isLoading,
    error
  };
};
