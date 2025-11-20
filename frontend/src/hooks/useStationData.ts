import { useState, useEffect, useCallback } from 'react';
import { API_BASE_URL } from '../config/layers';
import { MonitoringData, Station } from '../types/map.types';

export const useStationData = (
  showMonitoringStations: boolean,
  selectedCountry: string | null,
  selectedBasin: string | null
) => {
  const [monitoringData, setMonitoringData] = useState<MonitoringData | null>(null);
  const [selectedStation, setSelectedStation] = useState<Station | null>(null);
  const [isLoadingData, setIsLoadingData] = useState(false);

  const fetchStationData = useCallback(async () => {
    if (!showMonitoringStations) return;

    setIsLoadingData(true);
    try {
      const params = new URLSearchParams();
      if (selectedCountry) params.append('country', selectedCountry);
      if (selectedBasin) params.append('basin', selectedBasin);

      const url = `${API_BASE_URL}/monitoring-stations/?${params.toString()}`;
      const response = await fetch(url);
      
      if (!response.ok) throw new Error('Failed to fetch station data');
      
      const data = await response.json();
      setMonitoringData(data);
    } catch (error) {
      console.error('Error fetching station data:', error);
      setMonitoringData(null);
    } finally {
      setIsLoadingData(false);
    }
  }, [showMonitoringStations, selectedCountry, selectedBasin]);

  useEffect(() => {
    fetchStationData();
  }, [fetchStationData]);

  return {
    monitoringData,
    selectedStation,
    setSelectedStation,
    isLoadingData
  };
};
