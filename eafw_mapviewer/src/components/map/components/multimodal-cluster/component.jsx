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

    // Add individual point layer - colors based on alert_level
    map.addLayer({
      id: UNCLUSTERED_LAYER_ID,
      type: "circle",
      source: SOURCE_ID,
      paint: {
        // Color based on alert level - uses colors from shared config
        "circle-color": [
          "match",
          ["get", "alert_level"],
          "emergency", colors.emergency,
          "alarm", colors.alarm,
          "warning", colors.warning,
          "normal", colors.normal,
          colors.normal, // default
        ],
        "circle-radius": 3,
        "circle-stroke-width": 1,
        "circle-stroke-color": "#fff",
        "circle-opacity": 0.85,
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
