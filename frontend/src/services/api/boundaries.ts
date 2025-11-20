/**
 * Boundaries API Service
 * Handles administrative boundaries and water bodies
 */

import { API_ENDPOINTS } from '../../config';
import { CACHE_DURATION } from '../../config/constants';
import { fetchWithCache } from './base';

export interface BoundaryFeature {
  type: 'Feature';
  geometry: {
    type: string;
    coordinates: any;
  };
  properties: {
    ADM0_NAME?: string;
    ADM1_NAME?: string;
    ADM2_NAME?: string;
    ADMIN?: string;
    country?: string;
    [key: string]: any;
  };
}

export interface BoundaryDataResponse {
  type: 'FeatureCollection';
  features: BoundaryFeature[];
}

/**
 * Boundaries API client
 */
export const boundariesApi = {
  /**
   * Get Admin 0 (countries) boundaries
   */
  getAdmin0: async (): Promise<BoundaryDataResponse> => {
    return fetchWithCache<BoundaryDataResponse>(
      API_ENDPOINTS.boundaries.admin0,
      CACHE_DURATION.BOUNDARY_DATA
    );
  },

  /**
   * Get Admin 1 (provinces/states) boundaries
   */
  getAdmin1: async (): Promise<BoundaryDataResponse> => {
    return fetchWithCache<BoundaryDataResponse>(
      API_ENDPOINTS.boundaries.admin1,
      CACHE_DURATION.BOUNDARY_DATA
    );
  },

  /**
   * Get Admin 2 (districts) boundaries
   */
  getAdmin2: async (): Promise<BoundaryDataResponse> => {
    return fetchWithCache<BoundaryDataResponse>(
      API_ENDPOINTS.boundaries.admin2,
      CACHE_DURATION.BOUNDARY_DATA
    );
  },

  /**
   * Get water bodies
   */
  getWaterBodies: async (): Promise<BoundaryDataResponse> => {
    return fetchWithCache<BoundaryDataResponse>(
      API_ENDPOINTS.boundaries.waterbodies,
      CACHE_DURATION.BOUNDARY_DATA
    );
  },
};
