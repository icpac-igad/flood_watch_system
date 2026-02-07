/**
 * Regional Maps Widget - Optimized
 * Uses a single map for regional overview instead of 11 separate maps
 * Shows country detail view when a specific country is selected
 */
import React, { useState, useEffect, useRef, useMemo, useCallback, memo } from "react";
import PropTypes from "prop-types";
import maplibregl from "maplibre-gl";
import { CMS_API } from "@/utils/constants";
import Loader from "@/components/ui/loader";

import "./styles.scss";

// GHA Countries configuration
const GHA_COUNTRIES = [
  { code: "Burundi", name: "Burundi", adminPrefix: "BD", bounds: [[28.9, -4.5], [30.9, -2.3]], color: "#1976d2" },
  { code: "Djibouti", name: "Djibouti", adminPrefix: "DJ", bounds: [[41.7, 10.9], [43.5, 12.8]], color: "#388e3c" },
  { code: "Eritrea", name: "Eritrea", adminPrefix: "ER", bounds: [[36.4, 12.3], [43.2, 18.1]], color: "#f57c00" },
  { code: "Ethiopia", name: "Ethiopia", adminPrefix: "ET", bounds: [[33.0, 3.4], [48.0, 15.0]], color: "#7b1fa2" },
  { code: "Kenya", name: "Kenya", adminPrefix: "KE", bounds: [[33.9, -4.7], [42.0, 5.0]], color: "#c62828" },
  { code: "Rwanda", name: "Rwanda", adminPrefix: "RW", bounds: [[28.8, -2.9], [30.9, -1.0]], color: "#00838f" },
  { code: "Somalia", name: "Somalia", adminPrefix: "SO", bounds: [[40.9, -1.7], [51.5, 12.0]], color: "#5d4037" },
  { code: "South Sudan", name: "South Sudan", adminPrefix: "SS", bounds: [[23.4, 3.5], [36.0, 12.3]], color: "#1565c0" },
  { code: "Sudan", name: "Sudan", adminPrefix: "SD", bounds: [[21.8, 8.7], [38.6, 22.2]], color: "#6a1b9a" },
  { code: "Tanzania", name: "Tanzania", adminPrefix: "TZ", bounds: [[29.3, -11.8], [40.5, -1.0]], color: "#2e7d32" },
  { code: "Uganda", name: "Uganda", adminPrefix: "UG", bounds: [[29.5, -1.5], [35.1, 4.3]], color: "#d84315" },
];

// Alert level colors
const ALERT_COLORS = {
  emergency: "#F44336",
  alarm: "#FF9800",
  warning: "#FFC107",
  normal: "#4CAF50",
};

// GHA region bounds
const GHA_BOUNDS = [[21, -12], [52, 23]];

// Default map style - lightweight
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

// Country card component (no map, just summary data)
const CountryCard = memo(({ country, alertCounts, onClick, isSelected }) => {
  const totalAlerts = (alertCounts?.emergency || 0) + (alertCounts?.alarm || 0) + (alertCounts?.warning || 0);
  const maxLevel = alertCounts?.emergency > 0 ? "emergency" :
                   alertCounts?.alarm > 0 ? "alarm" :
                   alertCounts?.warning > 0 ? "warning" : "normal";

  return (
    <div
      className={`country-card ${isSelected ? "selected" : ""}`}
      onClick={() => onClick(country)}
      style={{ borderLeftColor: country.color }}
    >
      <div className="card-header">
        <h4>{country.name}</h4>
        <span className="alert-badge" style={{ backgroundColor: ALERT_COLORS[maxLevel] }}>
          {totalAlerts > 0 ? totalAlerts : "OK"}
        </span>
      </div>
      <div className="alert-summary">
        {alertCounts?.emergency > 0 && <span className="alert-count emergency">{alertCounts.emergency} Em</span>}
        {alertCounts?.alarm > 0 && <span className="alert-count alarm">{alertCounts.alarm} Al</span>}
        {alertCounts?.warning > 0 && <span className="alert-count warning">{alertCounts.warning} Wn</span>}
        {totalAlerts === 0 && <span className="alert-count normal">Normal</span>}
      </div>
    </div>
  );
});

CountryCard.displayName = "CountryCard";

// Regional Overview - Single map with all countries
const RegionalOverview = memo(({ forecastDate, alertFilter, countrySummary, onCountrySelect, selectedCountry }) => {
  const mapContainer = useRef(null);
  const map = useRef(null);
  const [loading, setLoading] = useState(true);

  // Initialize map once
  useEffect(() => {
    if (map.current) return;

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: DEFAULT_STYLE,
      bounds: GHA_BOUNDS,
      fitBoundsOptions: { padding: 20 },
    });

    map.current.addControl(new maplibregl.NavigationControl(), "top-right");

    map.current.on("load", () => {
      // Add country boundaries
      map.current.addSource("countries", {
        type: "vector",
        tiles: [`${window.location.origin}/pg/tileserv/gha.admin0/{z}/{x}/{y}.pbf`],
      });

      map.current.addLayer({
        id: "country-fill",
        type: "fill",
        source: "countries",
        "source-layer": "gha.admin0",
        paint: { "fill-color": "#e0e0e0", "fill-opacity": 0.3 },
      });

      map.current.addLayer({
        id: "country-outline",
        type: "line",
        source: "countries",
        "source-layer": "gha.admin0",
        paint: { "line-color": "#666", "line-width": 1 },
      });

      // Add forecast points source (GeoJSON)
      map.current.addSource("forecast-points", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });

      // Forecast points layer with alert colors
      map.current.addLayer({
        id: "forecast-points-layer",
        type: "circle",
        source: "forecast-points",
        paint: {
          "circle-radius": 5,
          "circle-color": [
            "match",
            ["get", "alert_level"],
            "emergency", ALERT_COLORS.emergency,
            "alarm", ALERT_COLORS.alarm,
            "warning", ALERT_COLORS.warning,
            "normal", ALERT_COLORS.normal,
            "#FFC107",
          ],
          "circle-stroke-width": 1,
          "circle-stroke-color": "#fff",
        },
      });

      // Hover effect on countries
      map.current.on("click", "country-fill", (e) => {
        const country = e.features[0]?.properties?.country;
        if (country) {
          const countryData = GHA_COUNTRIES.find((c) => c.code === country);
          if (countryData && onCountrySelect) {
            onCountrySelect(countryData);
          }
        }
      });

      map.current.on("mouseenter", "country-fill", () => {
        map.current.getCanvas().style.cursor = "pointer";
      });

      map.current.on("mouseleave", "country-fill", () => {
        map.current.getCanvas().style.cursor = "";
      });

      setLoading(false);
    });

    return () => {
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, [onCountrySelect]);

  // Fetch and update points when date/filter changes
  useEffect(() => {
    if (!map.current || !forecastDate) return;

    const controller = new AbortController();

    const fetchPoints = async () => {
      try {
        const filterParam = alertFilter && alertFilter !== "all" ? `&filter=${alertFilter}` : "";
        const url = `${CMS_API}/multimodal/geojson/?date=${forecastDate}${filterParam}`;
        const response = await fetch(url, { signal: controller.signal });

        if (response.ok) {
          const data = await response.json();
          if (map.current && map.current.getSource("forecast-points")) {
            map.current.getSource("forecast-points").setData(data);
          }
        }
      } catch (error) {
        if (error.name !== "AbortError") {
          console.error("Failed to fetch points:", error);
        }
      }
    };

    if (map.current.isStyleLoaded()) {
      fetchPoints();
    } else {
      map.current.once("load", fetchPoints);
    }

    return () => controller.abort();
  }, [forecastDate, alertFilter]);

  return (
    <div className="regional-overview">
      <div className="overview-content">
        {/* Map section */}
        <div className="overview-map-container">
          {loading && <div className="map-loader"><Loader /></div>}
          <div ref={mapContainer} className="overview-map" />

          {/* Legend */}
          <div className="map-legend">
            <div className="legend-title">Alert Levels</div>
            {Object.entries(ALERT_COLORS).map(([level, color]) => (
              <div key={level} className="legend-item">
                <span className="legend-dot" style={{ backgroundColor: color }} />
                {level.charAt(0).toUpperCase() + level.slice(1)}
              </div>
            ))}
          </div>
        </div>

        {/* Country cards sidebar */}
        <div className="countries-sidebar">
          <h4>Countries</h4>
          <div className="countries-list">
            {GHA_COUNTRIES.map((country) => (
              <CountryCard
                key={country.code}
                country={country}
                alertCounts={countrySummary?.[country.code]}
                onClick={onCountrySelect}
                isSelected={selectedCountry?.code === country.code}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
});

RegionalOverview.displayName = "RegionalOverview";

// Country Detail View - shown when a specific country is selected
const CountryDetailView = memo(({ country, forecastDate, alertFilter, onBack }) => {
  const mapContainer = useRef(null);
  const map = useRef(null);
  const [loading, setLoading] = useState(true);
  const [inundationData, setInundationData] = useState(null);

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

      // Forecast points source
      map.current.addSource("forecast-points", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });

      map.current.addLayer({
        id: "forecast-points-layer",
        type: "circle",
        source: "forecast-points",
        paint: {
          "circle-radius": 6,
          "circle-color": [
            "match",
            ["get", "alert_level"],
            "emergency", ALERT_COLORS.emergency,
            "alarm", ALERT_COLORS.alarm,
            "warning", ALERT_COLORS.warning,
            "normal", ALERT_COLORS.normal,
            "#FFC107",
          ],
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

  // Fetch filtered points
  useEffect(() => {
    if (!map.current || !forecastDate) return;

    const controller = new AbortController();

    const fetchPoints = async () => {
      try {
        const filterParam = alertFilter && alertFilter !== "all" ? `&filter=${alertFilter}` : "";
        const url = `${CMS_API}/multimodal/geojson/?date=${forecastDate}${filterParam}&country=${encodeURIComponent(country.code)}`;
        const response = await fetch(url, { signal: controller.signal });

        if (response.ok) {
          const data = await response.json();
          if (map.current && map.current.getSource("forecast-points")) {
            map.current.getSource("forecast-points").setData(data);
          }
        }
      } catch (error) {
        if (error.name !== "AbortError") {
          console.error("Failed to fetch points:", error);
        }
      }
    };

    if (map.current?.isStyleLoaded()) {
      fetchPoints();
    } else if (map.current) {
      map.current.once("load", fetchPoints);
    }

    return () => controller.abort();
  }, [forecastDate, alertFilter, country.code]);

  // Fetch inundation data
  useEffect(() => {
    const controller = new AbortController();

    const fetchInundation = async () => {
      try {
        const response = await fetch(
          `${CMS_API}/country-inundation/?country=${country.code}&date=${forecastDate || ""}`,
          { signal: controller.signal }
        );
        if (response.ok) {
          const data = await response.json();
          setInundationData(data);
        }
      } catch (error) {
        if (error.name !== "AbortError") {
          setInundationData({
            affected_population: "N/A",
            affected_area_km2: "N/A",
            affected_cropland_km2: "N/A",
            affected_infrastructure: "N/A",
          });
        }
      }
    };

    fetchInundation();
    return () => controller.abort();
  }, [country.code, forecastDate]);

  return (
    <div className="country-detail-view">
      <div className="detail-header" style={{ borderLeftColor: country.color }}>
        <button className="back-btn" onClick={onBack}>Back to Regional Report</button>
        <h3>{country.name} - Flood Report Details</h3>
        <p>Detailed report section for {forecastDate}</p>
      </div>

      <div className="detail-content">
        <div className="detail-map-container">
          {loading && <div className="map-loader"><Loader /></div>}
          <div ref={mapContainer} className="detail-map" />

          <div className="map-legend">
            <div className="legend-title">Alert Levels</div>
            {Object.entries(ALERT_COLORS).map(([level, color]) => (
              <div key={level} className="legend-item">
                <span className="legend-dot" style={{ backgroundColor: color }} />
                {level.charAt(0).toUpperCase() + level.slice(1)}
              </div>
            ))}
          </div>
        </div>

        <div className="inundation-widget">
          <h4>Potential Inundation Impact</h4>
          <p className="inundation-subtitle">Estimated impacts based on flood forecast</p>

          <div className="inundation-grid">
            <div className="inundation-card">
              <div className="inundation-label">Affected Population</div>
              <div className="inundation-value">{inundationData?.affected_population || "Loading..."}</div>
            </div>
            <div className="inundation-card">
              <div className="inundation-label">Affected Area</div>
              <div className="inundation-value">{inundationData?.affected_area_km2 || "Loading..."}</div>
            </div>
            <div className="inundation-card">
              <div className="inundation-label">Affected Cropland</div>
              <div className="inundation-value">{inundationData?.affected_cropland_km2 || "Loading..."}</div>
            </div>
            <div className="inundation-card">
              <div className="inundation-label">Infrastructure at Risk</div>
              <div className="inundation-value">{inundationData?.affected_infrastructure || "Loading..."}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
});

CountryDetailView.displayName = "CountryDetailView";

// Main Regional Maps component
const RegionalMapsWidget = ({ params, forecastDate, alertFilter, onCountrySelect }) => {
  const [selectedCountry, setSelectedCountry] = useState(null);
  const [countrySummary, setCountrySummary] = useState({});

  // Fetch summary data for all countries in a single request
  useEffect(() => {
    if (!forecastDate) return;

    const controller = new AbortController();

    const fetchSummary = async () => {
      try {
        const response = await fetch(
          `${CMS_API}/situation-summary/?date=${forecastDate}`,
          { signal: controller.signal }
        );
        if (response.ok) {
          const data = await response.json();
          // Transform country_breakdown to keyed object
          const summary = {};
          (data.country_breakdown || []).forEach((item) => {
            summary[item.country] = {
              emergency: item.emergency || 0,
              alarm: item.alarm || 0,
              warning: item.warning || 0,
              normal: item.normal || 0,
            };
          });
          setCountrySummary(summary);
        }
      } catch (error) {
        if (error.name !== "AbortError") {
          console.error("Failed to fetch summary:", error);
        }
      }
    };

    fetchSummary();
    return () => controller.abort();
  }, [forecastDate]);

  // Check if country selected via params
  const countryFromParams = useMemo(() => {
    if (!params?.admin0_code) return null;
    return GHA_COUNTRIES.find((c) => c.code === params.admin0_code || c.name === params.admin0_code);
  }, [params?.admin0_code]);

  const activeCountry = countryFromParams || selectedCountry;

  const handleCountryClick = useCallback((country) => {
    setSelectedCountry((prev) => (prev?.code === country.code ? null : country));
    if (onCountrySelect) onCountrySelect(country);
  }, [onCountrySelect]);

  const handleBack = useCallback(() => {
    setSelectedCountry(null);
  }, []);

  // Show detail view if country selected
  if (activeCountry) {
    return (
      <div className="c-regional-maps">
        <CountryDetailView
          country={activeCountry}
          forecastDate={forecastDate}
          alertFilter={alertFilter}
          onBack={handleBack}
        />
      </div>
    );
  }

  // Regional overview
  return (
    <div className="c-regional-maps">
      <div className="widget-header">
        <h3>Regional Report Section</h3>
        <p>Click on a country to open its detailed report section</p>
      </div>

      <RegionalOverview
        forecastDate={forecastDate}
        alertFilter={alertFilter}
        countrySummary={countrySummary}
        onCountrySelect={handleCountryClick}
        selectedCountry={selectedCountry}
      />
    </div>
  );
};

RegionalMapsWidget.propTypes = {
  params: PropTypes.object,
  forecastDate: PropTypes.string,
  alertFilter: PropTypes.string,
  onCountrySelect: PropTypes.func,
};

export default memo(RegionalMapsWidget);
