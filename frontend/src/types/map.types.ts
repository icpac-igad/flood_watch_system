import { LatLngTuple, LatLngBoundsExpression } from 'leaflet';

// Alert and Layer Types
export type AlertStatus = 'Normal' | 'Warning' | 'Alarm' | 'Emergency';
export type LayerType = 'ibew' | 'inundation' | 'impact' | string;

// Map Configuration Types
export interface MapServerConfig {
  mapserverWMSUrl: string;
  mapcacheWMSUrl: string;
  mapcacheTMSUrl: string;
}

export interface GHAView {
  center: LatLngTuple;
  zoom: number;
}

export interface MapConfig extends MapServerConfig {
  initialPosition: LatLngTuple;
  initialZoom: number;
  maxBounds: LatLngBoundsExpression;
  minZoom: number;
  maxZoom: number;
  getFeatureInfoFormat: string;
  ghaView: GHAView;
}

// Station Types
export interface StationStyle {
  radius: number;
  fillColor: string;
  color: string;
  weight: number;
  opacity: number;
  fillOpacity: number;
  selectedFillColor: string;
}

export interface StationConfig {
  style: StationStyle;
}

export interface StationProperties {
  Q_THR1?: number;
  q_thr1?: number;
  Q_THR2?: number;
  q_thr2?: number;
  Q_THR3?: number;
  q_thr3?: number;
  status?: string;
  Status?: string;
  [key: string]: any;
}

export interface Station {
  properties: StationProperties;
}

// Layer Types
export interface WMSLayer {
  name: string;
  layer: string;
  legend: string;
  isMapServer: boolean;
  useCache: boolean;
  wmsUrl: string;
  needsDate: boolean;
}

export interface BaseMap {
  name: string;
  url: string;
  attribution: string;
}

// GeoJSON Types
export interface MonitoringDataFeature {
  properties: StationProperties;
  geometry?: any;
}

export interface MonitoringData {
  features: MonitoringDataFeature[];
}

// Date selection state
export interface DateSelection {
  global: string | null;
}

// Layer visibility state
export interface LayerVisibility {
  showMonitoringStations: boolean;
  showGeoFSM: boolean;
  showMikeHydro: boolean;
  showHype: boolean;
  showEnsemble: boolean;
}

// API response types
export interface AvailableDatesResponse {
  dates: string[];
  detailed_dates: Array<{ date: string; count: number }>;
  count: number;
  latest: string | null;
}

export interface ForecastDataResponse {
  type: 'FeatureCollection';
  features: MonitoringDataFeature[];
}
