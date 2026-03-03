import React, { useEffect, useRef, useState, useCallback, useMemo } from "react";
import PropTypes from "prop-types";
import { connect } from "react-redux";

import { setMapInteractions } from "@/components/map/actions";
import { getMultimodalClusterConfig } from "@/providers/config-provider/selectors";
import { getActiveDatasetsFromState } from "@/components/map/selectors";

// Import shared configuration - single source of truth
import {
  DEFAULT_THRESHOLDS,
  ALERT_COLORS,
  ALERT_PRIORITY,
  calculateAlertLevelFromForecasts,
  getAlertPriority,
  mergeConfig,
} from "@/utils/multimodal-config";

// API base URL from environment
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";

// Source and layer IDs
const SOURCE_ID = "multimodal-cluster-source";
const CLUSTER_LAYER_ID = "multimodal-clusters";
const CLUSTER_COUNT_LAYER_ID = "multimodal-cluster-count";
const UNCLUSTERED_LAYER_ID = "multimodal-unclustered-point";
const GAUGE_ICON_IDS = Object.freeze({
  emergency: "multimodal-gauge-icon-emergency",
  alarm: "multimodal-gauge-icon-alarm",
  warning: "multimodal-gauge-icon-warning",
  normal: "multimodal-gauge-icon-normal",
});

const createGaugeIconCanvas = (color = ALERT_COLORS.normal) => {
  const canvas = document.createElement("canvas");
  const size = 48;
  canvas.width = size;
  canvas.height = size;

  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return { width: 1, height: 1, data: new Uint8Array([0, 0, 0, 0]) };
  }

  const centerX = 24;
  const centerY = 29;
  const radius = 12;

  ctx.lineCap = "round";
  ctx.lineJoin = "round";

  // White halo for contrast.
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 7;
  ctx.beginPath();
  ctx.arc(centerX, centerY, radius, Math.PI, 0, false);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(centerX, centerY);
  ctx.lineTo(centerX + 8, centerY - 8);
  ctx.stroke();
  ctx.fillStyle = "#ffffff";
  ctx.beginPath();
  ctx.arc(centerX, centerY, 4.5, 0, Math.PI * 2);
  ctx.fill();

  // CAP color layer.
  ctx.strokeStyle = color;
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.arc(centerX, centerY, radius, Math.PI, 0, false);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(centerX, centerY);
  ctx.lineTo(centerX + 8, centerY - 8);
  ctx.stroke();
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(centerX, centerY, 3.2, 0, Math.PI * 2);
  ctx.fill();

  const imageData = ctx.getImageData(0, 0, size, size);
  return { width: size, height: size, data: imageData.data };
};

const ensureGaugeIcons = (map, colors = ALERT_COLORS) => {
  Object.entries(GAUGE_ICON_IDS).forEach(([level, iconId]) => {
    if (map.hasImage(iconId)) {
      try {
        map.removeImage(iconId);
      } catch (error) {
        // Ignore remove race and continue with fresh add.
      }
    }
    map.addImage(iconId, createGaugeIconCanvas(colors[level] || colors.normal || ALERT_COLORS.normal), {
      pixelRatio: 2,
    });
  });
};

const buildGaugeIconExpression = () => [
  "match",
  ["get", "alert_level"],
  "emergency", GAUGE_ICON_IDS.emergency,
  "alarm", GAUGE_ICON_IDS.alarm,
  "warning", GAUGE_ICON_IDS.warning,
  GAUGE_ICON_IDS.normal,
];

/**
 * Get selected date from multimodal layer params in active datasets
 */
const getMultimodalSelectedDate = (activeDatasets) => {
  if (!activeDatasets || !Array.isArray(activeDatasets)) return null;

  for (const datasetConfig of activeDatasets) {
    const isMultimodal =
      datasetConfig.dataset?.toLowerCase().includes("multimodal") ||
      datasetConfig.dataset?.toLowerCase().includes("multi-model") ||
      datasetConfig.layers?.some(
        (l) =>
          l?.toLowerCase().includes("multimodal") ||
          l?.toLowerCase().includes("multi-model")
      );

    if (isMultimodal && datasetConfig.params?.time) {
      return datasetConfig.params.time;
    }
  }

  for (const datasetConfig of activeDatasets) {
    if (datasetConfig.params?.time) {
      return datasetConfig.params.time;
    }
  }

  return null;
};

/**
 * MultimodalClusterLayer Component
 * Displays multimodal forecast points on the map
 * Uses shared configuration from multimodal-config.js
 */
const MultimodalClusterLayer = ({
  map,
  setMapInteractions,
  clusterConfig,
  activeDatasets,
  visible = true,
}) => {
  const [geojsonData, setGeojsonData] = useState(null);
  const [loading, setLoading] = useState(false);
  const sourceAddedRef = useRef(false);

  // Get selected date from active datasets
  const selectedDate = useMemo(() => {
    const date = getMultimodalSelectedDate(activeDatasets);
    console.log(`[MultimodalCluster] selectedDate changed to: ${date}`, activeDatasets);
    return date;
  }, [activeDatasets]);

  const clickHandlerRef = useRef(null);
  const mouseEnterHandlerRef = useRef(null);
  const mouseLeaveHandlerRef = useRef(null);

  // Merge CMS config with defaults - uses shared config
  const config = useMemo(() => mergeConfig(clusterConfig), [clusterConfig]);

  // Check if layer is enabled
  const isEnabled = clusterConfig?.enableClustering !== false;

  // Fetch multimodal GeoJSON data
  const fetchData = useCallback(async () => {
    if (!isEnabled) return;

    console.log(`[MultimodalCluster] fetchData called with selectedDate: ${selectedDate}`);
    setLoading(true);
    try {
      let url = `${API_BASE_URL}/api/v1/multimodal/geojson/`;
      if (selectedDate) {
        url += `?date=${selectedDate}`;
      }

      console.log(`[MultimodalCluster] Fetching data from: ${url}`);
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error("Failed to fetch multimodal data");
      }
      const data = await response.json();

      // Process features to add alert_level using shared calculation
      if (data.features) {
        data.features = data.features.map((feature) => {
          const props = feature.properties || {};

          // Parse forecasts
          let forecasts = props.forecasts;
          if (typeof forecasts === "string") {
            try {
              forecasts = JSON.parse(forecasts);
            } catch (e) {
              forecasts = null;
            }
          }

          // Use shared function to calculate alert level - pass selectedDate for correct calculation
          const alertLevel = calculateAlertLevelFromForecasts(forecasts, config.thresholds, selectedDate);
          const priority = getAlertPriority(alertLevel);

          console.log(`[MultimodalCluster] Point ${props.admin_name}: date=${selectedDate}, alertLevel=${alertLevel}`);

          return {
            ...feature,
            properties: {
              ...props,
              alert_level: alertLevel,
              alert_priority: priority,
            },
          };
        });
      }

      // Log summary of alert levels
      const alertCounts = data.features?.reduce((acc, f) => {
        const level = f.properties?.alert_level || 'unknown';
        acc[level] = (acc[level] || 0) + 1;
        return acc;
      }, {});
      console.log(`[MultimodalCluster] Alert level summary for date ${selectedDate}:`, alertCounts);

      setGeojsonData(data);
    } catch (err) {
      console.error("Error fetching multimodal data:", err);
    } finally {
      setLoading(false);
    }
  }, [isEnabled, config.thresholds, selectedDate]);

  // Add source and layers to map
  const addClusterLayers = useCallback(() => {
    if (!map || !geojsonData || sourceAddedRef.current || !isEnabled) return;

    const { colors } = config;

    // Remove existing source/layers if they exist
    try {
      if (map.getLayer(UNCLUSTERED_LAYER_ID)) map.removeLayer(UNCLUSTERED_LAYER_ID);
      if (map.getLayer(CLUSTER_COUNT_LAYER_ID)) map.removeLayer(CLUSTER_COUNT_LAYER_ID);
      if (map.getLayer(CLUSTER_LAYER_ID)) map.removeLayer(CLUSTER_LAYER_ID);
      if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID);
    } catch (e) {
      // Layers may not exist
    }

    // Add GeoJSON source (clustering disabled for now - focus on individual points)
    map.addSource(SOURCE_ID, {
      type: "geojson",
      data: geojsonData,
      cluster: false, // Disabled - focus on individual point coloring first
    });

    ensureGaugeIcons(map, colors);

    // Add individual point layer - same gauge icon, CAP color by alert level.
    map.addLayer({
      id: UNCLUSTERED_LAYER_ID,
      type: "symbol",
      source: SOURCE_ID,
      layout: {
        "icon-image": buildGaugeIconExpression(),
        "icon-size": [
          "interpolate",
          ["linear"],
          ["zoom"],
          3, 0.52,
          8, 0.72,
          12, 0.92,
        ],
        "icon-allow-overlap": true,
        "icon-ignore-placement": true,
      },
      paint: {
        "icon-opacity": 0.9,
      },
    });

    sourceAddedRef.current = true;

    // Click handler for points
    clickHandlerRef.current = (e) => {
      const features = map.queryRenderedFeatures(e.point, {
        layers: [UNCLUSTERED_LAYER_ID],
      });

      if (!features.length) return;

      const feature = features[0];
      const { lngLat } = e;

      // Get coordinates from geometry
      const [featureLon, featureLat] = feature.geometry?.coordinates || [lngLat.lng, lngLat.lat];

      // Layer config for popup
      const layerConfig = {
        id: UNCLUSTERED_LAYER_ID,
        source: UNCLUSTERED_LAYER_ID,
        name: "Multi-Model Forecast",
        interactionConfig: {
          type: "intersection",
          output: [
            { column: "admin_name", property: "Location", type: "string" },
            { column: "point_id", property: "Point ID", type: "number", hidden: true },
            { column: "alert_level", property: "Alert Level", type: "string" },
            { column: "hybas_id", property: "Basin ID", type: "number", hidden: true },
            { column: "feature_lon", property: "Longitude", type: "number", hidden: true },
            { column: "feature_lat", property: "Latitude", type: "number", hidden: true },
            { column: "forecasts", property: "Forecasts", type: "string", hidden: true },
          ],
        },
      };

      // Build interaction feature with coordinates
      const interactionFeature = {
        ...feature.properties,
        feature_lon: featureLon,
        feature_lat: featureLat,
        geometry: feature.geometry,
        layer: layerConfig,
      };

      console.log(`[MultimodalCluster] Clicked point: ${feature.properties.admin_name}, alert_level: ${feature.properties.alert_level}, point_id: ${feature.properties.point_id}`);

      setMapInteractions({
        features: [interactionFeature],
        lngLat,
      });
    };

    map.on("click", UNCLUSTERED_LAYER_ID, clickHandlerRef.current);

    // Cursor handlers
    mouseEnterHandlerRef.current = () => {
      map.getCanvas().style.cursor = "pointer";
    };
    mouseLeaveHandlerRef.current = () => {
      map.getCanvas().style.cursor = "";
    };

    map.on("mouseenter", UNCLUSTERED_LAYER_ID, mouseEnterHandlerRef.current);
    map.on("mouseleave", UNCLUSTERED_LAYER_ID, mouseLeaveHandlerRef.current);
  }, [map, geojsonData, setMapInteractions, isEnabled, config]);

  // Update layer visibility
  const updateVisibility = useCallback(() => {
    if (!map || !sourceAddedRef.current) return;

    const visibility = visible && isEnabled ? "visible" : "none";
    try {
      if (map.getLayer(UNCLUSTERED_LAYER_ID)) {
        map.setLayoutProperty(UNCLUSTERED_LAYER_ID, "visibility", visibility);
      }
    } catch (e) {
      // Layer may not exist yet
    }
  }, [map, visible, isEnabled]);

  // Cleanup function
  const cleanup = useCallback(() => {
    if (!map) return;

    try {
      if (clickHandlerRef.current) {
        map.off("click", UNCLUSTERED_LAYER_ID, clickHandlerRef.current);
      }
      if (mouseEnterHandlerRef.current) {
        map.off("mouseenter", UNCLUSTERED_LAYER_ID, mouseEnterHandlerRef.current);
      }
      if (mouseLeaveHandlerRef.current) {
        map.off("mouseleave", UNCLUSTERED_LAYER_ID, mouseLeaveHandlerRef.current);
      }

      if (map.getLayer(UNCLUSTERED_LAYER_ID)) map.removeLayer(UNCLUSTERED_LAYER_ID);
      if (map.getLayer(CLUSTER_COUNT_LAYER_ID)) map.removeLayer(CLUSTER_COUNT_LAYER_ID);
      if (map.getLayer(CLUSTER_LAYER_ID)) map.removeLayer(CLUSTER_LAYER_ID);
      if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID);
    } catch (e) {
      // Ignore cleanup errors
    }

    sourceAddedRef.current = false;
  }, [map]);

  // Fetch data on mount and when selectedDate changes
  useEffect(() => {
    if (isEnabled) {
      fetchData();
    }
  }, [fetchData, isEnabled, selectedDate]);

  // Update map source when data changes
  useEffect(() => {
    if (!map || !geojsonData || !isEnabled) return;

    if (sourceAddedRef.current && map.getSource(SOURCE_ID)) {
      console.log("[MultimodalCluster] Updating existing source with new data");
      map.getSource(SOURCE_ID).setData(geojsonData);
      return;
    }

    if (!sourceAddedRef.current) {
      if (map.loaded()) {
        addClusterLayers();
      } else {
        map.on("load", addClusterLayers);
        return () => map.off("load", addClusterLayers);
      }
    }
  }, [map, geojsonData, addClusterLayers, isEnabled]);

  // Update visibility when prop changes
  useEffect(() => {
    updateVisibility();
  }, [updateVisibility]);

  // Cleanup on unmount
  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  return null;
};

MultimodalClusterLayer.propTypes = {
  map: PropTypes.object.isRequired,
  setMapInteractions: PropTypes.func.isRequired,
  clusterConfig: PropTypes.object,
  activeDatasets: PropTypes.array,
  visible: PropTypes.bool,
};

const mapStateToProps = (state) => ({
  clusterConfig: getMultimodalClusterConfig(state),
  activeDatasets: getActiveDatasetsFromState(state),
});

export default connect(mapStateToProps, { setMapInteractions })(MultimodalClusterLayer);
