/**
 * Custom hook for fetching admin boundaries data
 */

import { useState, useEffect } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8094/api';

interface AdminBoundariesData {
  type: 'FeatureCollection';
  features: any[];
}

interface UseAdminBoundariesReturn {
  admin0Data: AdminBoundariesData | null;
  admin1Data: AdminBoundariesData | null;
  admin2Data: AdminBoundariesData | null;
  isLoading: boolean;
  error: string | null;
}

export const useAdminBoundaries = (): UseAdminBoundariesReturn => {
  const [admin0Data, setAdmin0Data] = useState<AdminBoundariesData | null>(null);
  const [admin1Data, setAdmin1Data] = useState<AdminBoundariesData | null>(null);
  const [admin2Data, setAdmin2Data] = useState<AdminBoundariesData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadAdminBoundaries = async () => {
      try {
        // Fetch all admin levels in parallel
        const [admin1Response, admin2Response] = await Promise.all([
          fetch(`${API_BASE_URL}/admin1/`),
          fetch(`${API_BASE_URL}/admin2/`)
        ]);

        if (admin1Response.ok) {
          const data = await admin1Response.json();
          setAdmin1Data(data);
        }

        if (admin2Response.ok) {
          const data = await admin2Response.json();
          setAdmin2Data(data);
        }

        // Admin0 (country boundaries) - usually from WMS, not API
        // Keep as null for now, will be handled by WMS layer
        setAdmin0Data(null);

      } catch (err: any) {
        console.error('❌ Error loading admin boundaries:', err.message);
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };

    loadAdminBoundaries();
  }, []);

  return {
    admin0Data,
    admin1Data,
    admin2Data,
    isLoading,
    error
  };
};
