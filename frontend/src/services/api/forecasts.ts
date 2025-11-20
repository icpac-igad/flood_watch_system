/**
 * Forecast API Service
 * Handles deterministic and GeoSFM forecast data
 */

import { API_ENDPOINTS } from '../../config';
import { CACHE_DURATION } from '../../config/constants';
import { fetchJSON, fetchWithCache } from './base';

export interface ForecastDate {
  date: string;
  date_string: string;
  feature_count: number;
  file_count: number;
  created_at: string;
}

export interface AvailableDatesResponse {
  dates: ForecastDate[];
  count: number;
  latest: string | null;
}

export interface ForecastFeature {
  type: 'Feature';
  geometry: {
    type: string;
    coordinates: number[];
  };
  properties: {
    [key: string]: any;
  };
}

export interface ForecastDataResponse {
  type: 'FeatureCollection';
  features: ForecastFeature[];
}

/**
 * Forecast API client
 */
export const forecastsApi = {
  /**
   * Get available forecast dates (deterministic)
   */
  getAvailableDates: async (): Promise<AvailableDatesResponse> => {
    return fetchWithCache<AvailableDatesResponse>(
      API_ENDPOINTS.forecasts.deterministic.dates,
      CACHE_DURATION.AVAILABLE_DATES
    );
  },

  /**
   * Get forecast data for a specific date (deterministic)
   */
  getForecastByDate: async (date: string): Promise<ForecastDataResponse> => {
    return fetchWithCache<ForecastDataResponse>(
      API_ENDPOINTS.forecasts.deterministic.byDate(date),
      CACHE_DURATION.FORECAST_DATA
    );
  },

  /**
   * Get latest forecast data (deterministic)
   */
  getLatestForecast: async (): Promise<ForecastDataResponse> => {
    return fetchJSON<ForecastDataResponse>(
      API_ENDPOINTS.forecasts.deterministic.latest
    );
  },

  /**
   * Get available GeoSFM dates
   */
  getGeoSFMDates: async (): Promise<{ dates: string[] }> => {
    return fetchWithCache<{ dates: string[] }>(
      API_ENDPOINTS.forecasts.geosfm.dates,
      CACHE_DURATION.AVAILABLE_DATES
    );
  },

  /**
   * Get GeoSFM data for a specific date
   */
  getGeoSFMByDate: async (date: string): Promise<ForecastDataResponse> => {
    return fetchJSON<ForecastDataResponse>(
      API_ENDPOINTS.forecasts.geosfm.byDate(date)
    );
  },
};
