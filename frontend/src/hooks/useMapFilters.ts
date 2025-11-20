import { useState, useCallback } from 'react';

interface DateFilters {
  global: string;
  [key: string]: string;
}

export const useMapFilters = () => {
  const [selectedCountry, setSelectedCountry] = useState<string | null>(null);
  const [selectedBasin, setSelectedBasin] = useState<string | null>(null);
  const [selectedDates, setSelectedDates] = useState<DateFilters>({ 
    global: new Date().toISOString().split('T')[0] 
  });

  const handleDateChange = useCallback((key: string, date: string) => {
    setSelectedDates(prev => ({
      ...prev,
      [key]: date
    }));
  }, []);

  const handleCountryChange = useCallback((country: string | null) => {
    setSelectedCountry(country);
    setSelectedBasin(null);
  }, []);

  const handleBasinChange = useCallback((basin: string | null) => {
    setSelectedBasin(basin);
  }, []);

  return {
    selectedCountry,
    selectedBasin,
    selectedDates,
    handleDateChange,
    handleCountryChange,
    handleBasinChange,
    setSelectedCountry,
    setSelectedBasin
  };
};
