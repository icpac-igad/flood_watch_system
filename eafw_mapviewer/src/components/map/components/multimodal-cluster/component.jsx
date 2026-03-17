import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import PropTypes from "prop-types";
import { connect } from "react-redux";

import { setMapInteractions } from "@/components/map/actions";
import { getMultimodalClusterConfig } from "@/providers/config-provider/selectors";
import { getActiveDatasetsFromState } from "@/components/map/selectors";

// Import shared configuration - single source of truth
import {
  ALERT_COLORS,
  calculateAlertLevelFromForecasts,
  getAlertPriority,
  loadStormIconToMap,
  mergeConfig,
} from "@/utils/multimodal-config";

// API base URL from environment
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";

// Source and layer IDs
const SOURCE_ID = "multimodal-cluster-source";
const CLUSTER_LAYER_ID = "multimodal-clusters";
const UNCLUSTERED_LAYER_ID = "multimodal-unclustered-point";

// Storm icon IDs per alert level (individual points)
const STORM_ICON_IDS = Object.freeze({
  emergency: "storm-icon-emergency",
  alarm: "storm-icon-alarm",
  warning: "storm-icon-warning",
  normal: "storm-icon-normal",
});

// Cluster storm icon IDs (bigger, colored by worst alert level)
const CLUSTER_ICON_IDS = Object.freeze({
  emergency: "storm-cluster-emergency",
  alarm: "storm-cluster-alarm",
  warning: "storm-cluster-warning",
  normal: "storm-cluster-normal",
});

const POINT_ICON_SIZE = 28;
const CLUSTER_ICON_SIZE = 44;

const ensureStormIcons = async (map, colors = ALERT_COLORS) => {
  const promises = [];
  // Individual point icons (small)
  Object.entries(STORM_ICON_IDS).forEach(([level, iconId]) => {
    promises.push(loadStormIconToMap(map, iconId, colors[level] || colors.normal, POINT_ICON_SIZE));
  });
  // Cluster icons (big)
  Object.entries(CLUSTER_ICON_IDS).forEach(([level, iconId]) => {
    promises.push(loadStormIconToMap(map, iconId, colors[level] || colors.normal, CLUSTER_ICON_SIZE));
  });
  await Promise.all(promises);
};

const buildStormIconExpression = () => [
  "match",
  ["get", "alert_level"],
  "emergency", STORM_ICON_IDS.emergency,
  "alarm", STORM_ICON_IDS.alarm,
  "warning", STORM_ICON_IDS.warning,
  STORM_ICON_IDS.normal,
];

// Pick cluster icon by worst alert level in the cluster
const buildClusterIconExpression = () => [
  "case",
  [">", ["get", "has_emergency"], 0], CLUSTER_ICON_IDS.emergency,
  [">", ["get", "has_alarm"], 0], CLUSTER_ICON_IDS.alarm,
  [">", ["get", "has_warning"], 0], CLUSTER_ICON_IDS.warning,
  CLUSTER_ICON_IDS.normal,
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
  const [, setLoading] = useState(false);
  const sourceAddedRef = useRef(false);

  // Get selected date from active datasets
  const selectedDate = useMemo(() => {
    const date = getMultimodalSelectedDate(activeDatasets);
    console.log(`[MultimodalCluster] selectedDate changed to: ${date}`, activeDatasets);
    return date;
  }, [activeDatasets]);

  const clickHandlerRef = useRef(null);
  const clusterClickHandlerRef = useRef(null);
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
  const addClusterLayers = useCallback(async () => {
    if (!map || !geojsonData || sourceAddedRef.current || !isEnabled) return;

    const { colors } = config;

    // Remove existing source/layers if they exist
    try {
      if (map.getLayer(UNCLUSTERED_LAYER_ID)) map.removeLayer(UNCLUSTERED_LAYER_ID);
      if (map.getLayer(CLUSTER_LAYER_ID)) map.removeLayer(CLUSTER_LAYER_ID);
      if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID);
    } catch (e) {
      // Layers may not exist
    }

    // Add GeoJSON source with clustering and worst-alert-level aggregation
    map.addSource(SOURCE_ID, {
      type: "geojson",
      data: geojsonData,
      cluster: true,
      clusterRadius: 60,
      clusterMaxZoom: 8,
      clusterProperties: {
        has_emergency: ["+", ["case", ["==", ["get", "alert_level"], "emergency"], 1, 0]],
        has_alarm: ["+", ["case", ["==", ["get", "alert_level"], "alarm"], 1, 0]],
        has_warning: ["+", ["case", ["==", ["get", "alert_level"], "warning"], 1, 0]],
      },
    });

    await ensureStormIcons(map, colors);

    // Cluster layer — big storm icon colored by worst alert level
    map.addLayer({
      id: CLUSTER_LAYER_ID,
      type: "symbol",
      source: SOURCE_ID,
      filter: ["has", "point_count"],
      layout: {
        "icon-image": buildClusterIconExpression(),
        "icon-size": 1,
        "icon-allow-overlap": true,
        "icon-anchor": "center",
      },
      paint: {
        "icon-opacity": 0.92,
      },
    });

    // Individual point layer — small storm icon colored by alert level
    map.addLayer({
      id: UNCLUSTERED_LAYER_ID,
      type: "symbol",
      source: SOURCE_ID,
      filter: ["!", ["has", "point_count"]],
      layout: {
        "icon-image": buildStormIconExpression(),
        "icon-size": [
          "interpolate",
          ["linear"],
          ["zoom"],
          3, 0.65,
          8, 0.9,
          12, 1.15,
        ],
        "icon-allow-overlap": true,
        "icon-ignore-placement": true,
        "icon-anchor": "center",
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

    // Cluster click handler — zoom to expand
    clusterClickHandlerRef.current = (e) => {
      const features = map.queryRenderedFeatures(e.point, {
        layers: [CLUSTER_LAYER_ID],
      });
      if (!features.length) return;
      const clusterId = features[0].properties.cluster_id;
      map.getSource(SOURCE_ID).getClusterExpansionZoom(clusterId, (err, zoom) => {
        if (err) return;
        map.easeTo({
          center: features[0].geometry.coordinates,
          zoom: zoom,
        });
      });
    };
    map.on("click", CLUSTER_LAYER_ID, clusterClickHandlerRef.current);

    // Cursor handlers for both layers
    mouseEnterHandlerRef.current = () => {
      map.getCanvas().style.cursor = "pointer";
    };
    mouseLeaveHandlerRef.current = () => {
      map.getCanvas().style.cursor = "";
    };

    [UNCLUSTERED_LAYER_ID, CLUSTER_LAYER_ID].forEach((layerId) => {
      map.on("mouseenter", layerId, mouseEnterHandlerRef.current);
      map.on("mouseleave", layerId, mouseLeaveHandlerRef.current);
    });
  }, [map, geojsonData, setMapInteractions, isEnabled, config]);

  // Update layer visibility
  const updateVisibility = useCallback(() => {
    if (!map || !sourceAddedRef.current) return;

    const visibility = visible && isEnabled ? "visible" : "none";
    try {
      [UNCLUSTERED_LAYER_ID, CLUSTER_LAYER_ID].forEach((layerId) => {
        if (map.getLayer(layerId)) {
          map.setLayoutProperty(layerId, "visibility", visibility);
        }
      });
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
      if (clusterClickHandlerRef.current) {
        map.off("click", CLUSTER_LAYER_ID, clusterClickHandlerRef.current);
      }
      [UNCLUSTERED_LAYER_ID, CLUSTER_LAYER_ID].forEach((layerId) => {
        if (mouseEnterHandlerRef.current) {
          map.off("mouseenter", layerId, mouseEnterHandlerRef.current);
        }
        if (mouseLeaveHandlerRef.current) {
          map.off("mouseleave", layerId, mouseLeaveHandlerRef.current);
        }
      });

      if (map.getLayer(UNCLUSTERED_LAYER_ID)) map.removeLayer(UNCLUSTERED_LAYER_ID);
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
