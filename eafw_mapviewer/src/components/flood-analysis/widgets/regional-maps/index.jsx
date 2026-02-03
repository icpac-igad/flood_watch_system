/**
 * Regional Maps Widget
 * Shows map widgets for each GHA country/region by default
 * If a country is selected, shows detailed view with inundation info
 */
import React, { useState, useEffect, useRef } from "react";
import PropTypes from "prop-types";
import maplibregl from "maplibre-gl";
import { CMS_API } from "@/utils/constants";
import Loader from "@/components/ui/loader";

import "./styles.scss";

// GHA Countries configuration
const GHA_COUNTRIES = [
  { code: "Burundi", name: "Burundi", bounds: [[28.9, -4.5], [30.9, -2.3]], color: "#1976d2" },
  { code: "Djibouti", name: "Djibouti", bounds: [[41.7, 10.9], [43.5, 12.8]], color: "#388e3c" },
  { code: "Eritrea", name: "Eritrea", bounds: [[36.4, 12.3], [43.2, 18.1]], color: "#f57c00" },
  { code: "Ethiopia", name: "Ethiopia", bounds: [[33.0, 3.4], [48.0, 15.0]], color: "#7b1fa2" },
  { code: "Kenya", name: "Kenya", bounds: [[33.9, -4.7], [42.0, 5.0]], color: "#c62828" },
  { code: "Rwanda", name: "Rwanda", bounds: [[28.8, -2.9], [30.9, -1.0]], color: "#00838f" },
  { code: "Somalia", name: "Somalia", bounds: [[40.9, -1.7], [51.5, 12.0]], color: "#5d4037" },
  { code: "South Sudan", name: "South Sudan", bounds: [[23.4, 3.5], [36.0, 12.3]], color: "#1565c0" },
  { code: "Sudan", name: "Sudan", bounds: [[21.8, 8.7], [38.6, 22.2]], color: "#6a1b9a" },
  { code: "Tanzania", name: "Tanzania", bounds: [[29.3, -11.8], [40.5, -1.0]], color: "#2e7d32" },
  { code: "Uganda", name: "Uganda", bounds: [[29.5, -1.5], [35.1, 4.3]], color: "#d84315" },
];

// Alert level colors
const ALERT_COLORS = {
  emergency: "#F44336",
  alarm: "#FF9800",
  warning: "#FFC107",
  normal: "#4CAF50",
};

// Default map style
const DEFAULT_STYLE = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
    },
  },
  layers: [{ id: "osm", type: "raster", source: "osm" }],
};

// Single country map widget (for regional grid)
const CountryMapWidget = ({ country, forecastDate, onClick, isSelected }) => {
  const mapContainer = useRef(null);
  const map = useRef(null);
  const [loading, setLoading] = useState(true);
  const [alertCounts, setAlertCounts] = useState({ emergency: 0, alarm: 0, warning: 0, normal: 0 });

  useEffect(() => {
    if (map.current) return;

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: DEFAULT_STYLE,
      bounds: country.bounds,
      fitBoundsOptions: { padding: 10 },
      interactive: false,
    });

    map.current.on("load", () => {
      map.current.addSource("country-boundary", {
        type: "vector",
        tiles: [`${window.location.origin}/pg/tileserv/gha.admin0/{z}/{x}/{y}.pbf`],
      });

      map.current.addLayer({
        id: "country-fill",
        type: "fill",
        source: "country-boundary",
        "source-layer": "gha.admin0",
        paint: { "fill-color": country.color, "fill-opacity": 0.2 },
        filter: ["==", "country", country.code],
      });

      map.current.addLayer({
        id: "country-outline",
        type: "line",
        source: "country-boundary",
        "source-layer": "gha.admin0",
        paint: { "line-color": country.color, "line-width": 2 },
        filter: ["==", "country", country.code],
      });

      map.current.addSource("forecast-points", {
        type: "vector",
        tiles: [`${window.location.origin}/pg/tileserv/gha.multimodal_control_points/{z}/{x}/{y}.pbf`],
      });

      map.current.addLayer({
        id: "forecast-points-layer",
        type: "circle",
        source: "forecast-points",
        "source-layer": "gha.multimodal_control_points",
        paint: {
          "circle-radius": 3,
          "circle-color": "#FFC107",
          "circle-stroke-width": 0.5,
          "circle-stroke-color": "#fff",
        },
      });

      setLoading(false);
    });

    return () => {
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, [country]);

  useEffect(() => {
    const fetchAlertCounts = async () => {
      try {
        const response = await fetch(
          `${CMS_API}/country-alerts/?country=${country.code}&date=${forecastDate || ""}`
        );
        if (response.ok) {
          const data = await response.json();
          setAlertCounts(data.counts || { emergency: 0, alarm: 0, warning: 0, normal: 0 });
        }
      } catch (error) {
        // Use default counts
      }
    };
    fetchAlertCounts();
  }, [country.code, forecastDate]);

  const totalAlerts = alertCounts.emergency + alertCounts.alarm + alertCounts.warning;
  const maxLevel = alertCounts.emergency > 0 ? "emergency" :
                   alertCounts.alarm > 0 ? "alarm" :
                   alertCounts.warning > 0 ? "warning" : "normal";

  return (
    <div
      className={`country-map-widget ${isSelected ? "selected" : ""}`}
      onClick={() => onClick(country)}
      style={{ borderColor: isSelected ? country.color : "#ddd" }}
    >
      <div className="widget-header">
        <h4 style={{ color: country.color }}>{country.name}</h4>
        <span className="alert-badge" style={{ backgroundColor: ALERT_COLORS[maxLevel] }}>
          {totalAlerts > 0 ? totalAlerts : "✓"}
        </span>
      </div>

      <div className="map-container-small">
        {loading && <div className="map-loader"><Loader /></div>}
        <div ref={mapContainer} className="map" />
      </div>

      <div className="alert-summary">
        {alertCounts.emergency > 0 && <span className="alert-count emergency">{alertCounts.emergency} Emergency</span>}
        {alertCounts.alarm > 0 && <span className="alert-count alarm">{alertCounts.alarm} Alarm</span>}
        {alertCounts.warning > 0 && <span className="alert-count warning">{alertCounts.warning} Warning</span>}
        {totalAlerts === 0 && <span className="alert-count normal">Normal conditions</span>}
      </div>
    </div>
  );
};

// Country Detail View - shown when a specific country is selected
const CountryDetailView = ({ country, forecastDate }) => {
  const mapContainer = useRef(null);
  const map = useRef(null);
  const [loading, setLoading] = useState(true);
  const [inundationData, setInundationData] = useState(null);
  const [alertCounts, setAlertCounts] = useState({ emergency: 0, alarm: 0, warning: 0, normal: 0 });

  useEffect(() => {
    if (map.current) return;

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: DEFAULT_STYLE,
      bounds: country.bounds,
      fitBoundsOptions: { padding: 30 },
    });

    map.current.addControl(new maplibregl.NavigationControl(), "top-right");

    map.current.on("load", () => {
      // Country boundary
      map.current.addSource("country-boundary", {
        type: "vector",
        tiles: [`${window.location.origin}/pg/tileserv/gha.admin0/{z}/{x}/{y}.pbf`],
      });

      map.current.addLayer({
        id: "country-fill",
        type: "fill",
        source: "country-boundary",
        "source-layer": "gha.admin0",
        paint: { "fill-color": country.color, "fill-opacity": 0.1 },
        filter: ["==", "country", country.code],
      });

      map.current.addLayer({
        id: "country-outline",
        type: "line",
        source: "country-boundary",
        "source-layer": "gha.admin0",
        paint: { "line-color": country.color, "line-width": 3 },
        filter: ["==", "country", country.code],
      });

      // Admin1 boundaries
      map.current.addSource("admin1", {
        type: "vector",
        tiles: [`${window.location.origin}/pg/tileserv/gha.admin1/{z}/{x}/{y}.pbf`],
      });

      map.current.addLayer({
        id: "admin1-outline",
        type: "line",
        source: "admin1",
        "source-layer": "gha.admin1",
        paint: { "line-color": "#666", "line-width": 1, "line-dasharray": [2, 2] },
        filter: ["==", "country", country.code],
      });

      // Forecast points with alert colors
      map.current.addSource("forecast-points", {
        type: "vector",
        tiles: [`${window.location.origin}/pg/tileserv/gha.multimodal_control_points/{z}/{x}/{y}.pbf`],
      });

      map.current.addLayer({
        id: "forecast-points-layer",
        type: "circle",
        source: "forecast-points",
        "source-layer": "gha.multimodal_control_points",
        paint: {
          "circle-radius": 4,
          "circle-color": "#FFC107",
          "circle-stroke-width": 1,
          "circle-stroke-color": "#fff",
        },
      });

      setLoading(false);
    });

    return () => {
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, [country]);

  // Fetch inundation data
  useEffect(() => {
    const fetchInundationData = async () => {
      try {
        const response = await fetch(
          `${CMS_API}/country-inundation/?country=${country.code}&date=${forecastDate || ""}`
        );
        if (response.ok) {
          const data = await response.json();
          setInundationData(data);
        }
      } catch (error) {
        // No inundation data available
        setInundationData({
          affected_population: "Data not available",
          affected_area_km2: "Data not available",
          affected_cropland_km2: "Data not available",
          affected_infrastructure: "Data not available",
        });
      }
    };
    fetchInundationData();
  }, [country.code, forecastDate]);

  return (
    <div className="country-detail-view">
      <div className="detail-header" style={{ borderLeftColor: country.color }}>
        <h3>{country.name} - Flood Forecast Details</h3>
        <p>Detailed analysis for {forecastDate}</p>
      </div>

      <div className="detail-content">
        {/* Large Map */}
        <div className="detail-map-container">
          {loading && <div className="map-loader"><Loader /></div>}
          <div ref={mapContainer} className="detail-map" />

          {/* Map Legend */}
          <div className="map-legend">
            <div className="legend-title">Alert Levels</div>
            <div className="legend-item">
              <span className="legend-dot" style={{ backgroundColor: ALERT_COLORS.emergency }} />
              Emergency
            </div>
            <div className="legend-item">
              <span className="legend-dot" style={{ backgroundColor: ALERT_COLORS.alarm }} />
              Alarm
            </div>
            <div className="legend-item">
              <span className="legend-dot" style={{ backgroundColor: ALERT_COLORS.warning }} />
              Warning
            </div>
            <div className="legend-item">
              <span className="legend-dot" style={{ backgroundColor: ALERT_COLORS.normal }} />
              Normal
            </div>
          </div>
        </div>

        {/* Inundation Widget */}
        <div className="inundation-widget">
          <h4>Potential Inundation Impact</h4>
          <p className="inundation-subtitle">Estimated impacts based on flood forecast</p>

          <div className="inundation-grid">
            <div className="inundation-card">
              <div className="inundation-icon">👥</div>
              <div className="inundation-label">Affected Population</div>
              <div className="inundation-value">
                {inundationData?.affected_population || "Loading..."}
              </div>
            </div>

            <div className="inundation-card">
              <div className="inundation-icon">🗺️</div>
              <div className="inundation-label">Affected Area</div>
              <div className="inundation-value">
                {inundationData?.affected_area_km2 || "Loading..."}
              </div>
            </div>

            <div className="inundation-card">
              <div className="inundation-icon">🌾</div>
              <div className="inundation-label">Affected Cropland</div>
              <div className="inundation-value">
                {inundationData?.affected_cropland_km2 || "Loading..."}
              </div>
            </div>

            <div className="inundation-card">
              <div className="inundation-icon">🏗️</div>
              <div className="inundation-label">Infrastructure at Risk</div>
              <div className="inundation-value">
                {inundationData?.affected_infrastructure || "Loading..."}
              </div>
            </div>
          </div>

          <div className="inundation-note">
            Note: These are estimated impacts based on flood extent modeling. Actual impacts may vary.
          </div>
        </div>
      </div>
    </div>
  );
};

// Main Regional Maps component
const RegionalMapsWidget = ({ params, forecastDate, onCountrySelect }) => {
  const [selectedCountry, setSelectedCountry] = useState(null);

  // If a country is selected via params, use that
  const countryFromParams = params?.admin0_code
    ? GHA_COUNTRIES.find((c) => c.code === params.admin0_code || c.name === params.admin0_code)
    : null;

  const activeCountry = countryFromParams || selectedCountry;

  const handleCountryClick = (country) => {
    setSelectedCountry(country.code === selectedCountry?.code ? null : country);
    if (onCountrySelect) {
      onCountrySelect(country);
    }
  };

  // If a specific country is selected, show detailed view
  if (activeCountry) {
    return (
      <div className="c-regional-maps">
        <CountryDetailView country={activeCountry} forecastDate={forecastDate} />
      </div>
    );
  }

  // Otherwise show regional overview with all countries
  return (
    <div className="c-regional-maps">
      <div className="widget-header">
        <h3>Regional Overview</h3>
        <p>Click on a country to view detailed analysis</p>
      </div>

      <div className="countries-grid">
        {GHA_COUNTRIES.map((country) => (
          <CountryMapWidget
            key={country.code}
            country={country}
            forecastDate={forecastDate}
            onClick={handleCountryClick}
            isSelected={selectedCountry?.code === country.code}
          />
        ))}
      </div>
    </div>
  );
};

RegionalMapsWidget.propTypes = {
  params: PropTypes.object,
  forecastDate: PropTypes.string,
  onCountrySelect: PropTypes.func,
};

export default RegionalMapsWidget;
