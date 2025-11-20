# MapViewer Refactoring Guide

This document explains the new modular structure for MapViewer and how to use it.

## Overview

The refactoring extracts complex logic into reusable custom hooks and components, making the code more maintainable and type-safe.

## New Structure

```
frontend/src/
├── types/
│   └── map.types.ts                    # TypeScript type definitions
├── hooks/
│   ├── index.ts                        # Centralized exports
│   ├── useForecastData.ts              # Multi-Model forecast data + caching
│   ├── useAvailableDates.ts            # Available forecast dates
│   ├── useLayerVisibility.ts           # Layer visibility state
│   ├── useGeoSFMData.ts                # GeoSFM forecast data
│   └── useAdminBoundaries.ts           # Admin boundaries (admin1, admin2)
├── components/
│   └── map/
│       └── layers/
│           ├── index.ts                # Centralized exports
│           ├── MonitoringStationsLayer.tsx  # Multi-Model stations
│           └── GeoSFMLayer.tsx         # GeoSFM hexagons
└── utils/
    └── forecastCache.js                # In-memory cache (existing)
```

## Usage Example

Here's how to use the new modular structure in MapViewer:

### 1. Import Custom Hooks and Components

```typescript
// Import all hooks from centralized export
import {
  useForecastData,
  useAvailableDates,
  useLayerVisibility,
  useGeoSFMData,
  useAdminBoundaries
} from '../../hooks';

// Import layer components from centralized export
import {
  MonitoringStationsLayer,
  GeoSFMLayer
} from '../map/layers';

// Import types
import { DateSelection } from '../../types/map.types';
```

### 2. Use Hooks in Component

```typescript
export const MapViewer: React.FC = () => {
  // Date selection state
  const [selectedDates, setSelectedDates] = useState<DateSelection>({
    global: null
  });
  const [selectedCountry, setSelectedCountry] = useState<string | null>(null);

  // Fetch available dates
  const { dates: availableDates, latestDate } = useAvailableDates();

  // Set initial date when available dates load
  useEffect(() => {
    if (latestDate && !selectedDates.global) {
      setSelectedDates({ global: latestDate });
    }
  }, [latestDate, selectedDates.global]);

  // Layer visibility management
  const { visibility, toggleLayer, setLayerVisibility } = useLayerVisibility();

  // Fetch Multi-Model forecast data with automatic caching
  const {
    data: monitoringData,
    isLoading: isLoadingData,
    error: dataError
  } = useForecastData({
    enabled: visibility.showMonitoringStations,
    selectedDate: selectedDates.global,
    selectedCountry,
    availableDates
  });

  // Fetch GeoSFM data
  const {
    data: geoSFMData,
    availableDates: geosfmDates,
    isLoading: geosfmLoading
  } = useGeoSFMData({
    enabled: visibility.showGeoFSM,
    selectedDate: selectedDates.global
  });

  // Fetch admin boundaries
  const {
    admin0Data,
    admin1Data,
    admin2Data,
    isLoading: adminLoading
  } = useAdminBoundaries();

  // Station selection
  const [selectedStation, setSelectedStation] = useState(null);

  // Handler for date changes
  const handleDateChange = useCallback((layerType: string, date: string) => {
    console.log(`📅 Date changed to: ${date}`);
    setSelectedDates({ global: date });
  }, []);

  // Handler for station clicks
  const handleStationClick = useCallback((feature) => {
    setSelectedStation(feature);
  }, []);

  // Handler for report generation
  const handleGenerateReport = useCallback((feature) => {
    // Your report generation logic
    console.log('Generate report for:', feature.properties.SEC_NAME);
  }, []);

  return (
    <MapContainer>
      {/* Base map tiles, WMS layers, etc. */}

      {/* Admin Boundaries (from database API) */}
      {admin1Data && (
        <GeoJSON
          data={admin1Data}
          style={{ color: '#666', weight: 1, fillOpacity: 0 }}
        />
      )}
      {admin2Data && (
        <GeoJSON
          data={admin2Data}
          style={{ color: '#999', weight: 0.5, fillOpacity: 0 }}
        />
      )}

      {/* Multi-Model Monitoring Stations Layer */}
      {visibility.showMonitoringStations && (
        <MonitoringStationsLayer
          data={monitoringData}
          selectedDate={selectedDates.global}
          selectedCountry={selectedCountry}
          selectedStation={selectedStation}
          onStationClick={handleStationClick}
          onGenerateReport={handleGenerateReport}
        />
      )}

      {/* GeoSFM Layer */}
      {visibility.showGeoFSM && (
        <GeoSFMLayer
          data={geoSFMData}
          selectedDate={selectedDates.global}
        />
      )}

      {/* Other layers (Mike Hydro, Hype, Ensemble) remain as WMS */}
    </MapContainer>
  );
};
```

## Key Benefits

### 1. **Automatic Data Fetching & Caching**
- `useForecastData` automatically fetches data when date/country changes
- Built-in cache checking for instant loads
- Handles loading and error states

### 2. **Type Safety**
- All props and state are typed
- Catches errors at compile time
- Better IDE autocomplete

### 3. **Separation of Concerns**
- Data fetching logic → `useForecastData`
- Date management → `useAvailableDates`
- Layer state → `useLayerVisibility`
- Rendering → `MonitoringStationsLayer`

### 4. **Reusability**
- Hooks can be reused in other components
- Easy to test in isolation
- Clear dependencies

### 5. **Fixed Date Selection Bug**
- `MonitoringStationsLayer` automatically unmounts/remounts when data changes
- No need to manually toggle layers
- Markers update instantly when date changes

## Migration Steps

To migrate existing MapViewer.jsx:

1. Add TypeScript types for your state
2. Replace inline data fetching with `useForecastData`
3. Replace date fetching with `useAvailableDates`
4. Replace layer state with `useLayerVisibility`
5. Replace marker rendering with `MonitoringStationsLayer`
6. Remove manual cache checks (handled by hook)
7. Remove manual unmount/remount logic (handled by component)

## Testing

The modular structure makes testing easier:

```typescript
// Test hook in isolation
const { result } = renderHook(() => useForecastData({
  enabled: true,
  selectedDate: '2025-11-01',
  selectedCountry: null,
  availableDates: ['2025-11-01']
}));

// Test component in isolation
render(
  <MonitoringStationsLayer
    data={mockData}
    selectedDate="2025-11-01"
    selectedCountry={null}
    selectedStation={null}
    onStationClick={mockFn}
    onGenerateReport={mockFn}
  />
);
```

## Performance

- **Caching**: Data cached in memory for instant subsequent loads
- **Lazy Loading**: Only fetches when layer is visible (`enabled` prop)
- **Optimized Re-renders**: React.memo and useCallback prevent unnecessary renders
- **Automatic Cleanup**: Hooks clean up effects when unmounted

## Complete Layer Support

The modular structure now supports all layers:

### Data Layers (with hooks)
1. **Multi-Model Discharge** → `useForecastData` + `MonitoringStationsLayer`
2. **GeoSFM** → `useGeoSFMData` + `GeoSFMLayer`
3. **Admin Boundaries** → `useAdminBoundaries` + standard `GeoJSON`

### WMS Layers (keep existing approach)
- Rivers, Lakes, Waterbodies → Use existing `StableWMSLayer`
- Inundation maps → Use existing WMS approach
- Mike Hydro, Hype, Ensemble → Use existing WMS approach

### Why Some Layers Stay as WMS?
- Rivers, lakes, waterbodies are **static** - don't change with dates
- Served directly by MapServer - very fast
- No need for data transformation or state management
- Keep what works!

## Quick Reference

### Import Everything You Need
```typescript
// All hooks in one import
import {
  useForecastData,        // Multi-Model data + caching
  useAvailableDates,      // Available dates
  useLayerVisibility,     // Layer on/off state
  useGeoSFMData,          // GeoSFM data
  useAdminBoundaries      // Admin boundaries
} from '../../hooks';

// All layer components in one import
import {
  MonitoringStationsLayer,  // Multi-Model markers
  GeoSFMLayer              // GeoSFM hexagons
} from '../map/layers';
```

### Hook Usage Pattern
```typescript
const { data, isLoading, error, refetch } = useXxxData({
  enabled: visibility.showXxx,    // Only fetch when layer is ON
  selectedDate: date,             // Current selected date
  selectedCountry: country,       // Optional country filter
  availableDates: dates           // For fallback
});
```

## Notes

- The original logic and functionality remain unchanged
- Same caching strategy (`forecastCache`)
- Same API endpoints
- Same user experience
- Just better organized and type-safe!
- WMS layers keep working as-is
- Admin boundaries load once on mount
- Forecast data refetches when date changes
