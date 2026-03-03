import React, { Component, PureComponent, createRef } from "react";
import PropTypes from "prop-types";
import isEqual from "lodash/isEqual";
import isEmpty from "lodash/isEmpty";
import debounce from "lodash/debounce";
import cx from "classnames";

import { trackMapLatLon, trackEvent } from "@/utils/analytics";
import { ALERT_COLORS, CLUSTER_ICON_PREFIX, SYMBOL_LAYOUT, DEFAULT_THRESHOLDS } from "@/utils/multimodal-config";
import { buildMultimodalClusterIconImageExpression } from "@/utils/layer-utils";

import Loader from "@/components/ui/loader";
import Icon from "@/components/ui/icon";
import Map from "@/components/ui/map";
import MapboxCompare from "./mapbox-compare";

import iconCrosshair from "@/assets/icons/crosshair.svg?sprite";

import Scale from "./components/scale";
import Popup from "./components/popup";
import MapToolTip from "./components/map-tooltip";
import Draw from "./components/draw";
import Attributions from "./components/attributions";

// Components
import LayerManagerWrapper from "./components/layer-manager";
import MultimodalClusterLayer from "./components/multimodal-cluster";
import AlertPulse from "./components/emergency-pulse";
import EmergencyClusterPulse from "./components/emergency-cluster-pulse";
import BasinLayer from "./components/basin-layer";
import NileBasinLayer from "./components/nile-basin-layer";
// import { pulsingDot } from "./mapImages";

import mapStyleForNoStyle from "./style";

// Styles
import "./styles.scss";

const EXTERNAL_BASEMAP_SOURCE_ID = "__external-basemap-source";
const EXTERNAL_BASEMAP_LAYER_ID = "__external-basemap-layer";
const MULTIMODAL_GAUGE_ICON_PREFIX = "multimodal-gauge-";
const MULTIMODAL_GAUGE_ICON_IDS = Object.freeze({
  emergency: `${MULTIMODAL_GAUGE_ICON_PREFIX}emergency`,
  alarm: `${MULTIMODAL_GAUGE_ICON_PREFIX}alarm`,
  warning: `${MULTIMODAL_GAUGE_ICON_PREFIX}warning`,
  normal: `${MULTIMODAL_GAUGE_ICON_PREFIX}normal`,
});

const MULTIMODAL_ALERT_LEVEL_EXPR = [
  "downcase",
  ["to-string", ["coalesce", ["get", "alert_level"], ""]],
];
const MULTIMODAL_DAILY_AVG_EXPR = ["to-number", ["coalesce", ["get", "daily_avg"], 0]];

const buildMultimodalGaugeIconExpression = () => ([
  "case",
  ["==", MULTIMODAL_ALERT_LEVEL_EXPR, "emergency"], MULTIMODAL_GAUGE_ICON_IDS.emergency,
  ["==", MULTIMODAL_ALERT_LEVEL_EXPR, "alarm"], MULTIMODAL_GAUGE_ICON_IDS.alarm,
  ["==", MULTIMODAL_ALERT_LEVEL_EXPR, "warning"], MULTIMODAL_GAUGE_ICON_IDS.warning,
  ["==", MULTIMODAL_ALERT_LEVEL_EXPR, "normal"], MULTIMODAL_GAUGE_ICON_IDS.normal,
  [">=", MULTIMODAL_DAILY_AVG_EXPR, DEFAULT_THRESHOLDS.emergency], MULTIMODAL_GAUGE_ICON_IDS.emergency,
  [">=", MULTIMODAL_DAILY_AVG_EXPR, DEFAULT_THRESHOLDS.alarm], MULTIMODAL_GAUGE_ICON_IDS.alarm,
  [">=", MULTIMODAL_DAILY_AVG_EXPR, DEFAULT_THRESHOLDS.warning], MULTIMODAL_GAUGE_ICON_IDS.warning,
  MULTIMODAL_GAUGE_ICON_IDS.normal,
]);

class RenderMap extends PureComponent {
  render() {
    const {
      mapStyle,
      viewport,
      bounds,
      onViewportChange,
      onClick,
      onMouseMove,
      onLoad,
      interactiveLayerIds,
      minZoom,
      maxZoom,
      onClickAnalysis,
      drawing,
      onDrawComplete,
      drawingMode,
      mapSide,
      style,
    } = this.props;

    return (
      <Map
        comparing={!!mapSide}
        mapStyle={mapStyle || mapStyleForNoStyle}
        viewport={viewport}
        bounds={bounds}
        onViewportChange={onViewportChange}
        onClick={onClick}
        onMouseMove={onMouseMove}
        onLoad={({ ...args }) => onLoad(args, mapSide)}
        interactiveLayerIds={interactiveLayerIds}
        attributionControl={false}
        minZoom={minZoom}
        maxZoom={maxZoom}
        style={style}
        getCursor={({ isHovering, isDragging }) => {
          if (drawing) return "crosshair";
          if (isDragging) return "grabbing";
          if (isHovering) return "pointer";
          return "grab";
        }}
      >
        {(map) => (
          <>
            {/* LAYER MANAGER */}
            <LayerManagerWrapper map={map} mapSide={mapSide} />

            {/* MULTIMODAL CLUSTERED LAYER - disabled: pg_tileserv handles clustering via vector tiles */}
            {/* <MultimodalClusterLayer map={map} mapSide={mapSide} /> */}

            {/* Alert Pulse (icon fade in/out) — disabled, keeping only the red expanding ring */}
            {/* <AlertPulse map={map} /> */}

            {/* Emergency Cluster Pulse - halo animation for clustered emergency points */}
            <EmergencyClusterPulse map={map} />

            {/* Basin Layer - Auto-loads basin boundary when clicking forecast points */}
            <BasinLayer map={map} />
            <NileBasinLayer map={map} />

            {!mapSide && (
              <>
                {/* POPUP */}
                <Popup map={map} onClickAnalysis={onClickAnalysis} />
                {/* Hover POPUP */}
                <MapToolTip />
                {/* DRAWING */}
                <Draw
                  map={map}
                  drawing={drawing}
                  onDrawComplete={onDrawComplete}
                  drawingMode={drawingMode}
                />
                {/* SCALE */}
                <Scale className="map-scale" map={map} viewport={viewport} />
                {/* ATTRIBUTIONS */}
                <Attributions
                  className="map-attributions"
                  map={map}
                  viewport={viewport}
                />
              </>
            )}
          </>
        )}
      </Map>
    );
  }
}

class MapComponent extends Component {
  static propTypes = {
    className: PropTypes.string,
    viewport: PropTypes.shape().isRequired,
    mapStyle: PropTypes.string,
    setMapSettings: PropTypes.func.isRequired,
    setMapInteractions: PropTypes.func.isRequired,
    clearMapInteractions: PropTypes.func.isRequired,
    setMapHoverInteraction: PropTypes.func.isRequired,
    clearMapHoverInteraction: PropTypes.func.isRequired,
    hasHoverFeature: PropTypes.bool,
    mapLabels: PropTypes.bool,
    mapRoads: PropTypes.bool,
    location: PropTypes.object,
    interactiveLayerIds: PropTypes.array,
    hoverableLayerIds: PropTypes.array,
    canBound: PropTypes.bool,
    stateBbox: PropTypes.array,
    geostoreBbox: PropTypes.array,
    interaction: PropTypes.object,
    minZoom: PropTypes.number.isRequired,
    maxZoom: PropTypes.number.isRequired,
    drawing: PropTypes.bool,
    loading: PropTypes.bool,
    loadingMessage: PropTypes.string,
    basemap: PropTypes.object,
    onClickAnalysis: PropTypes.func,
    onDrawComplete: PropTypes.func,
    lang: PropTypes.string,
    printRequests: PropTypes.number,
    mapPrinting: PropTypes.bool,
    onMapGetStyle: PropTypes.func,
    vectorLayerIcons: PropTypes.array,
  };

  state = {
    bounds: {},
    drawClicks: 0,
    leftMap: null,
    rightMap: null,
    compareMap: null,
  };

  mapCompareContainer = createRef();

  componentDidUpdate(prevProps, prevState) {
    const {
      mapLabels,
      mapRoads,
      setMapSettings,
      canBound,
      stateBbox,
      geostoreBbox,
      interaction,
      viewport,
      lang,
      drawing,
      clearMapInteractions,
      basemap,
      location,
      geostoreType,
      printRequests,
      boundaryBounds,
      vectorLayerIcons,
    } = this.props;

    const {
      mapLabels: prevMapLabels,
      mapRoads: prevMapRoads,
      stateBbox: prevStateBbox,
      geostoreBbox: prevGeostoreBbox,
      interaction: prevInteraction,
      lang: prevLang,
      drawing: prevDrawing,
      basemap: prevBasemap,
      location: prevLocation,
      printRequests: prevPrintRequests,
      boundaryBounds: prevBoundaryBounds,
      vectorLayerIcons: prevVectorLayerIcons,
    } = prevProps;

    if (!drawing && prevDrawing) {
      this.resetClicks();
    }

    if (drawing && !prevDrawing) {
      clearMapInteractions();
    }

    if (basemap?.basemapGroup !== prevBasemap.basemapGroup) {
      this.applyBaseMap();
      this.applyLabels();
    }

    if (mapLabels !== prevMapLabels || lang !== prevLang) {
      this.applyLabels();
    }

    if (mapRoads !== prevMapRoads) {
      this.applyRoads();
    }

    // if bbox is change by action fit bounds
    if (canBound && stateBbox?.length && stateBbox !== prevStateBbox) {
      // eslint-disable-next-line
      this.setState({ bounds: { bbox: stateBbox, options: { padding: 50 } } });
    }

    // if geostore changes
    if (canBound && geostoreBbox?.length && geostoreBbox !== prevGeostoreBbox) {
      if (location && location.type === "use" && geostoreType === "Point") {
        setMapSettings({
          zoom: 7,
          center: {
            lat: geostoreBbox[1],
            lng: geostoreBbox[0],
          },
        });
      } else {
        // eslint-disable-next-line
        this.setState({
          bounds: { bbox: geostoreBbox, options: { padding: 50 } },
        });
      }
    }

    // if clicked point changes
    if (location && location.type === "point") {
      // eslint-disable-next-line
      const { adm0, adm1 } = location;
      const prevLat = prevLocation.adm0;
      const prevLong = prevLocation.adm1;

      if (adm0 !== prevLat || adm1 !== prevLong) {
        const lat = parseFloat(adm0);
        const lng = parseFloat(adm1);

        setMapSettings({
          center: {
            lat: lat,
            lng: lng,
          },
        });
      }
    }

    // reset canBound after fitting bounds
    if (
      canBound &&
      !isEmpty(this.state.bounds) &&
      !isEqual(this.state.bounds, prevState.bounds)
    ) {
      setMapSettings({ canBound: false, bbox: [] });
      // eslint-disable-next-line
      this.setState({ bounds: {} });
    }

    // fit bounds on cluster if clicked
    if (interaction && !isEqual(interaction, prevInteraction)) {
      trackEvent({
        category: "Map analysis",
        action: "User opens analysis popup infowindow",
        label: interaction.label,
      });

      if (interaction.data.cluster) {
        const { data, layer, geometry } = interaction;
        this.map
          .getSource(layer.id)
          .getClusterExpansionZoom(data.cluster_id, (err, newZoom) => {
            if (err) return;
            const { coordinates } = geometry;
            const difference = Math.abs(viewport.zoom - newZoom);
            setMapSettings({
              center: {
                lat: coordinates[1],
                lng: coordinates[0],
              },
              zoom: newZoom,
              transitionDuration: 400 + difference * 100,
            });
          });
      }
    }

    // if print request incremented
    if (this.map && printRequests && printRequests !== prevPrintRequests) {
      this.requestPrintMap();
    }

    if (!isEqual(boundaryBounds, prevBoundaryBounds)) {
      this.setMapBoundaryBounds();
    }

    if (!isEqual(vectorLayerIcons, prevVectorLayerIcons)) {
      this.loadMapImages();
    }
  }

  componentWillUnmount() {
    if (this.map) {
      this.map.off("styledata", this.onStyleLoad);
      this.map.off("styleimagemissing", this.handleStyleImageMissing);
      this.map.off("idle", this.syncMultimodalIconOverlays);
    }
    if (this.state.compareMap) {
      this.state.compareMap.remove();
    }
  }

  // Generate a cluster bubble icon as ImageData for a given alert color
  createClusterIcon = (color, size = 40) => {
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');
    const cx = size / 2;
    const cy = size / 2;
    const r = size / 2 - 3;

    // Filled circle with white border
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2.5;
    ctx.stroke();

    return ctx.getImageData(0, 0, size, size);
  };

  // Generate gauge icon with circular ring around it
  createGaugeIcon = (color, size = 64) => {
    const canvas = document.createElement("canvas");
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;

    const cx = size / 2;
    const cy = size / 2;
    const ringRadius = size * 0.32;
    const gaugeRadius = size * 0.18;

    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    // Outer white halo ring
    ctx.beginPath();
    ctx.arc(cx, cy, ringRadius, 0, Math.PI * 2);
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = Math.max(4, size * 0.11);
    ctx.stroke();

    // CAP colored ring
    ctx.beginPath();
    ctx.arc(cx, cy, ringRadius, 0, Math.PI * 2);
    ctx.strokeStyle = color;
    ctx.lineWidth = Math.max(2, size * 0.05);
    ctx.stroke();

    // Gauge arc
    ctx.beginPath();
    ctx.arc(cx, cy + size * 0.05, gaugeRadius, Math.PI, 0, false);
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = Math.max(3, size * 0.08);
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(cx, cy + size * 0.05, gaugeRadius, Math.PI, 0, false);
    ctx.strokeStyle = color;
    ctx.lineWidth = Math.max(2, size * 0.05);
    ctx.stroke();

    // Needle + center pivot
    const pivotY = cy + size * 0.05;
    ctx.beginPath();
    ctx.moveTo(cx, pivotY);
    ctx.lineTo(cx + size * 0.12, pivotY - size * 0.12);
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = Math.max(3, size * 0.08);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(cx, pivotY);
    ctx.lineTo(cx + size * 0.12, pivotY - size * 0.12);
    ctx.strokeStyle = color;
    ctx.lineWidth = Math.max(2, size * 0.05);
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(cx, pivotY, Math.max(2.2, size * 0.04), 0, Math.PI * 2);
    ctx.fillStyle = "#ffffff";
    ctx.fill();

    ctx.beginPath();
    ctx.arc(cx, pivotY, Math.max(1.4, size * 0.025), 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();

    return ctx.getImageData(0, 0, size, size);
  };

  // Register cluster bubble icons for all alert levels
  loadClusterIcons = () => {
    if (!this.map) return;
    Object.entries(ALERT_COLORS).forEach(([level, color]) => {
      const name = `${CLUSTER_ICON_PREFIX}${level}`;
      if (this.map.hasImage(name)) return;
      const imageData = this.createClusterIcon(color);
      this.map.addImage(name, { width: imageData.width, height: imageData.height, data: imageData.data });
    });
  };

  // Register multimodal gauge icons for all alert levels
  loadGaugeIcons = () => {
    if (!this.map) return;
    Object.entries(ALERT_COLORS).forEach(([level, color]) => {
      const name = MULTIMODAL_GAUGE_ICON_IDS[level];
      if (!name) return;
      const imageData = this.createGaugeIcon(color);
      if (!imageData) return;
      if (this.map.hasImage(name)) {
        try {
          this.map.removeImage(name);
        } catch (error) {
          // Ignore race conditions while style is settling.
        }
      }
      this.map.addImage(name, { width: imageData.width, height: imageData.height, data: imageData.data });
    });
  };

  loadMapImages = async () => {
    const { vectorLayerIcons } = this.props;

    if (vectorLayerIcons && !!vectorLayerIcons.length && this.map) {
      vectorLayerIcons.forEach((icon) => {
        if (this.map.hasImage(icon.name)) return;

        this.map.loadImage(icon.url, (error, iconImage) => {
          if (!error && iconImage && !this.map.hasImage(icon.name)) {
            this.map.addImage(icon.name, iconImage);
          }
        });
      });
    }

    // Also generate cluster bubble icons
    this.loadClusterIcons();
    this.loadGaugeIcons();
  };

  // Handle missing images by loading them on-demand
  handleStyleImageMissing = (e) => {
    const { vectorLayerIcons } = this.props;
    const id = e.id;

    if (!this.map) return;

    // Check if it's a cluster icon request
    if (id.startsWith(CLUSTER_ICON_PREFIX)) {
      const level = id.replace(CLUSTER_ICON_PREFIX, '');
      const color = ALERT_COLORS[level];
      if (color && !this.map.hasImage(id)) {
        const imageData = this.createClusterIcon(color);
        this.map.addImage(id, { width: imageData.width, height: imageData.height, data: imageData.data });
      }
      return;
    }

    // Check if it's a multimodal gauge icon request
    if (id.startsWith(MULTIMODAL_GAUGE_ICON_PREFIX)) {
      const level = id.replace(MULTIMODAL_GAUGE_ICON_PREFIX, "");
      const color = ALERT_COLORS[level];
      if (color && !this.map.hasImage(id)) {
        const imageData = this.createGaugeIcon(color);
        if (imageData) {
          this.map.addImage(id, { width: imageData.width, height: imageData.height, data: imageData.data });
        }
      }
      return;
    }

    if (!vectorLayerIcons) return;

    const icon = vectorLayerIcons.find(i => i.name === id);
    if (icon && !this.map.hasImage(id)) {
      this.map.loadImage(icon.url, (error, iconImage) => {
        if (!error && iconImage && !this.map.hasImage(id)) {
          this.map.addImage(id, iconImage);
        }
      });
    }
  };

  // Overlay symbol icon layers on top of multimodal circle layers.
  // Runs on idle so the circle layers from layer-manager are already added.
  syncMultimodalIconOverlays = () => {
    if (!this.map) return;
    try {
      const style = this.map.getStyle();
      if (!style?.layers) return;

      const CLUSTER_ZOOM = 7;
      const ICON_SUFFIX = '__icon-overlay';
      const CLUSTER_ICON_SUFFIX = '__cluster-icon-overlay';

      // Find multimodal circle layers
      const circleLayers = style.layers.filter(
        (l) =>
          l.type === 'circle' &&
          typeof l['source-layer'] === 'string' &&
          l['source-layer'].includes('multimodal_points')
      );

      circleLayers.forEach((circleLayer) => {
        const pointIconId = circleLayer.id + ICON_SUFFIX;
        const clusterIconId = circleLayer.id + CLUSTER_ICON_SUFFIX;

        // Add individual point icon overlay (z >= cluster_zoom)
        if (!this.map.getLayer(pointIconId)) {
          try {
            this.map.addLayer({
              id: pointIconId,
              type: 'symbol',
              source: circleLayer.source,
                'source-layer': circleLayer['source-layer'],
                minzoom: CLUSTER_ZOOM,
                layout: {
                'icon-image': buildMultimodalGaugeIconExpression(),
                'icon-size': [
                  'interpolate', ['linear'], ['zoom'],
                  CLUSTER_ZOOM, 0.95,
                  CLUSTER_ZOOM + 3, 1.15,
                  14, 1.35
                ],
                'icon-allow-overlap': true,
                'icon-ignore-placement': true,
                'icon-anchor': 'center',
              },
              paint: {
                'icon-opacity': 0.95,
              },
            });
          } catch (e) { /* layer may already exist or style settling */ }
        }

        // Add cluster icon overlay (z < cluster_zoom)
        if (!this.map.getLayer(clusterIconId)) {
          try {
            this.map.addLayer({
              id: clusterIconId,
              type: 'symbol',
              source: circleLayer.source,
              'source-layer': circleLayer['source-layer'],
              maxzoom: CLUSTER_ZOOM,
              layout: {
                'icon-image': buildMultimodalClusterIconImageExpression(),
                'icon-size': SYMBOL_LAYOUT.clusterIconSize,
                'icon-allow-overlap': true,
                'icon-anchor': 'center',
                'text-field': ['to-string', ['get', 'point_count']],
                'text-size': SYMBOL_LAYOUT.clusterTextSize,
                'text-anchor': 'center',
                'text-offset': [0, 0],
                'text-allow-overlap': true,
              },
              paint: {
                'text-color': SYMBOL_LAYOUT.clusterTextColor,
                'text-halo-color': SYMBOL_LAYOUT.clusterTextHaloColor,
                'text-halo-width': SYMBOL_LAYOUT.clusterTextHaloWidth,
              },
            });
          } catch (e) { /* layer may already exist or style settling */ }
        }
      });

      // Hide underlying circles at z >= cluster_zoom where icons show
      circleLayers.forEach((circleLayer) => {
        try {
          // Make circles tiny at high zoom where pin icons display
          this.map.setPaintProperty(circleLayer.id, 'circle-opacity', [
            'interpolate', ['linear'], ['zoom'],
            CLUSTER_ZOOM - 0.5, 0.9,
            CLUSTER_ZOOM, 0,
          ]);
          this.map.setPaintProperty(circleLayer.id, 'circle-stroke-opacity', [
            'interpolate', ['linear'], ['zoom'],
            CLUSTER_ZOOM - 0.5, 1,
            CLUSTER_ZOOM, 0,
          ]);
        } catch (e) { /* ignore */ }
      });

      // Clean up orphan icon overlays (circle layer was removed)
      const activeCircleIds = new Set(circleLayers.map((l) => l.id));
      style.layers.forEach((l) => {
        if (l.id.endsWith(ICON_SUFFIX) || l.id.endsWith(CLUSTER_ICON_SUFFIX)) {
          const baseId = l.id.replace(ICON_SUFFIX, '').replace(CLUSTER_ICON_SUFFIX, '');
          if (!activeCircleIds.has(baseId)) {
            try { this.map.removeLayer(l.id); } catch (e) { /* ignore */ }
          }
        }
      });
    } catch (e) {
      // Style may not be ready yet
    }
  };

  fitMapBoundaryBounds = () => {
    const { mapBounds, boundaryBounds, location } = this.props;

    const { type, adm0 } = location;

    const hasMapBounds = mapBounds && !!mapBounds.length;

    if (
      (!type || (type === "country" && !adm0)) &&
      !hasMapBounds &&
      boundaryBounds &&
      !!boundaryBounds.length
    ) {
      this.setState({
        bounds: { bbox: boundaryBounds, options: { padding: 50 } },
      });
    }
  };

  onViewportChange = debounce((viewport, mapSide) => {
    const { setMapSettings, location } = this.props;
    const { latitude, longitude, bearing, pitch, zoom } = viewport;

    let mapBounds = this.map && this.map.getBounds().toArray();

    setMapSettings({
      center: {
        lat: latitude,
        lng: longitude,
      },
      mapBounds,
      bearing,
      pitch,
      zoom,
    });
    trackMapLatLon(location);
  }, 250);

  onStyleLoad = () => {
    this.applyBaseMap();
    this.applyLabels();
    this.applyRoads();
  };

  onLoad = ({ map, mapContainer }, mapSide) => {
    const { setMapSettings } = this.props;

    // remove any if existing
    if (this.state.compareMap) {
      this.state.compareMap.remove();
      this.setState({ compareMap: null });
    }

    this.map = null;

    if (mapSide) {
      if (mapSide === "left") {
        this.setState({ leftMap: map }, this.checkCompareMapsLoad);
      } else {
        this.setState({ rightMap: map }, this.checkCompareMapsLoad);
      }
    } else {
      this.map = map;
    }

    // Labels
    this.applyBaseMap();
    this.applyLabels();
    this.applyRoads();

    // const mapBounds = this.map.getBounds().toArray();

    // setMapSettings({
    //   mapBounds,
    // });

    if (this.map) {
      this.fitMapBoundaryBounds();

      // Listeners — use `on` (not `once`) so applyBaseMap re-runs
      // whenever the style URL changes (e.g. after ConfigProvider sets mapStyle).
      this.map.on("styledata", this.onStyleLoad);

      // Handle missing images on-demand
      this.map.on("styleimagemissing", this.handleStyleImageMissing);

      // Sync icon overlays when map becomes idle (layers are ready)
      this.map.on("idle", this.syncMultimodalIconOverlays);
    }

    this.loadMapImages();
  };

  checkCompareMapsLoad = () => {
    const { comparing } = this.props;
    const { leftMap, rightMap } = this.state;

    if (comparing && leftMap && rightMap) {
      const compareMap = new MapboxCompare(
        leftMap,
        rightMap,
        this.mapCompareContainer.current,
        { orientation: "vertical" }
      );

      this.setState({ compareMap: compareMap });
    }
  };

  requestPrintMap = () => {
    const { mapPrinting, setMapSettings, onGetMapPrintConfig, viewport } =
      this.props;

    if (!mapPrinting && onGetMapPrintConfig) {
      setMapSettings({ printing: true });

      onGetMapPrintConfig({
        mapStyle: this.map.getStyle(),
        viewport: viewport,
        bounds: this.map.getBounds().toArray(),
      });
    }
  };

  onClick = (e) => {
    const { drawing, clearMapInteractions } = this.props;
    if (!drawing && e.features && e.features.length) {
      const { features, lngLat } = e;
      const { setMapInteractions } = this.props;

      // Generic cluster handling for GeoJSON clustered sources.
      // Applies to modular model layers (GeoSFM/Floodproofs/Mike Hydro/Google/Hype).
      const geoJsonClusterFeature = features.find((feature) => {
        const sourceId = feature?.layer?.source;
        const source = sourceId && this.map ? this.map.getSource(sourceId) : null;
        const hasClusterFlag =
          feature?.properties?.cluster === true ||
          feature?.properties?.cluster === 1 ||
          feature?.properties?.cluster === "1";
        const hasClusterId = feature?.properties?.cluster_id !== undefined;
        return (
          hasClusterFlag &&
          hasClusterId &&
          source &&
          typeof source.getClusterExpansionZoom === "function"
        );
      });

      if (geoJsonClusterFeature && this.map) {
        clearMapInteractions();

        const sourceId = geoJsonClusterFeature?.layer?.source;
        const source = sourceId ? this.map.getSource(sourceId) : null;
        const clusterId = geoJsonClusterFeature?.properties?.cluster_id;
        const coordinates = geoJsonClusterFeature?.geometry?.coordinates;
        const hasLngLat = Array.isArray(coordinates) && coordinates.length >= 2;
        const [lng, lat] = hasLngLat ? coordinates : [lngLat[0], lngLat[1]];

        source.getClusterExpansionZoom(clusterId, (err, newZoom) => {
          if (err) return;
          const currentZoom = this.map.getZoom();
          const zoom = Number.isFinite(newZoom) ? newZoom : currentZoom + 1;
          const difference = Math.abs(currentZoom - zoom);
          this.map.easeTo({
            center: { lng, lat },
            zoom,
            duration: 500 + difference * 120,
            essential: true,
          });
        });
        return;
      }

      // FloodWatch Custom: Multi-model clusters are server-side (pg_tileserv) and shouldn't open the popup.
      // Clicking a cluster should zoom in until it breaks into points.
      const multimodalClusterFeature = features.find((feature) => {
        const sourceLayer =
          feature?.sourceLayer || feature?.layer?.["source-layer"];
        const hasPointId =
          feature?.properties?.point_id !== undefined &&
          feature?.properties?.point_id !== null &&
          feature?.properties?.point_id !== "";

        return (
          sourceLayer &&
          String(sourceLayer).includes("multimodal_points") &&
          // In clustered mode, tiles don't include point_id (chart should be point-only).
          !hasPointId
        );
      });

      if (multimodalClusterFeature && this.map) {
        // Close any open popup and zoom in to "open" the cluster.
        clearMapInteractions();

        const coordinates = multimodalClusterFeature?.geometry?.coordinates;
        const hasLngLat =
          Array.isArray(coordinates) && coordinates.length >= 2;
        const [lng, lat] = hasLngLat ? coordinates : [lngLat[0], lngLat[1]];

        // Infer the unclustered zoom threshold from the tile URL (cluster_zoom=...).
        const sourceId = multimodalClusterFeature?.layer?.source;
        const styleSource = sourceId
          ? this.map.getStyle()?.sources?.[sourceId]
          : null;
        const tileUrl = styleSource?.tiles?.[0] || "";
        let clusterZoom = 7;
        try {
          const query = tileUrl.split("?")[1] || "";
          const params = new URLSearchParams(query);
          const parsed = Number(params.get("cluster_zoom"));
          if (Number.isFinite(parsed) && parsed > 0) clusterZoom = parsed;
        } catch (err) {
          // ignore parsing errors
        }

        const currentZoom = this.map.getZoom();
        const maxZoom = typeof this.map.getMaxZoom === "function" ? this.map.getMaxZoom() : 19;
        // Make sure we cross into the "unclustered" tile zoom level.
        const targetZoom = Math.min(maxZoom, Math.max(currentZoom + 1, clusterZoom + 0.5));

        this.map.easeTo({
          center: { lng, lat },
          zoom: targetZoom,
          duration: 650,
          essential: true,
        });
        return;
      }

      setMapInteractions({
        features: features.map((f) => ({
          ...f,
          geometry: f.geometry,
          // _vectorTileFeature cannot be serialized by redux
          // so we must remove them before dispatching the action
          _vectorTileFeature: null,
        })),
        lngLat,
      });
    } else if (drawing) {
      this.setState({ drawClicks: this.state.drawClicks + 1 });
    } else {
      clearMapInteractions();
    }
  };

  onMouseMove = (e) => {
    const {
      hoverableLayerIds,
      clearMapHoverInteraction,
      hasHoverFeature,
      setMapHoverInteraction,
    } = this.props;

    if (hoverableLayerIds && !!hoverableLayerIds.length) {
      try {
        const features =
          this.map &&
          this.map.queryRenderedFeatures(e.point, { layers: hoverableLayerIds });
        if (features && !!features.length) {
          const { lngLat } = e;

          setMapHoverInteraction({ feature: features[0], lngLat });
        } else {
          hasHoverFeature && clearMapHoverInteraction();
        }
      } catch (err) {
        // Layer might not exist yet, ignore the error
      }
    }
  };

  applyBaseMap = () => {
    const { leftMap, rightMap } = this.state;

    if (!this.map) {
      if (leftMap) {
        this.setBasemap(leftMap);
      }
      if (rightMap) {
        this.setBasemap(rightMap);
      }
    } else {
      this.setBasemap(this.map);
    }
  };

  setBasemap = (map) => {
    const { basemap } = this.props;
    const BASEMAP_GROUPS = ["basemap"];

    const removeExternalBasemap = () => {
      if (map.getLayer(EXTERNAL_BASEMAP_LAYER_ID)) {
        map.removeLayer(EXTERNAL_BASEMAP_LAYER_ID);
      }
      if (map.getSource(EXTERNAL_BASEMAP_SOURCE_ID)) {
        map.removeSource(EXTERNAL_BASEMAP_SOURCE_ID);
      }
    };

    if (map && map.getStyle()) {
      const { layers = [], metadata = {} } = map.getStyle() || {};
      const mapboxGroups = metadata["mapbox:groups"] || {};

      const basemapGroups = Object.keys(mapboxGroups).filter((k) => {
        const { name } = mapboxGroups[k] || {};

        const matchedGroups = BASEMAP_GROUPS.map((rgr) =>
          name?.toLowerCase()?.includes(rgr)
        );

        return matchedGroups.some((bool) => bool);
      });

      const basemapLayers = layers.filter((l) => {
        const { metadata: layerMetadata } = l;
        if (!layerMetadata) return false;

        const gr = layerMetadata["mapbox:group"];
        return basemapGroups.includes(gr);
      });

      // URL basemaps are injected as a raster layer at the bottom of the style.
      // This allows providers like Google/ESRI/OSM while preserving all data overlays.
      if (basemap?.url) {
        basemapLayers.forEach((_layer) => {
          if (map.getLayer(_layer.id)) {
            map.setLayoutProperty(_layer.id, "visibility", "none");
          }
        });

        removeExternalBasemap();
        map.addSource(EXTERNAL_BASEMAP_SOURCE_ID, {
          type: "raster",
          tiles: [basemap.url],
          tileSize: 256,
        });

        const externalLayer = {
          id: EXTERNAL_BASEMAP_LAYER_ID,
          type: "raster",
          source: EXTERNAL_BASEMAP_SOURCE_ID,
          paint: {
            "raster-opacity": 1,
          },
        };

        const firstLayerId = layers?.[0]?.id;
        if (firstLayerId && map.getLayer(firstLayerId)) {
          map.addLayer(externalLayer, firstLayerId);
        } else {
          map.addLayer(externalLayer);
        }

        return true;
      }

      removeExternalBasemap();

      const basemapsWithMeta = basemapGroups.map((_groupId) => ({
        ...mapboxGroups[_groupId],
        id: _groupId,
      }));
      const basemapToDisplay = basemapsWithMeta.find((_basemap) =>
        _basemap?.name?.includes(basemap?.basemapGroup)
      );

      if (!basemapToDisplay) return true;

      basemapLayers.forEach((_layer) => {
        const match = _layer.metadata["mapbox:group"] === basemapToDisplay.id;
        if (map.getLayer(_layer.id)) {
          map.setLayoutProperty(_layer.id, "visibility", match ? "visible" : "none");
        }
      });
    }

    return true;
  };

  applyLabels = () => {
    const { leftMap, rightMap } = this.state;
    if (!this.map) {
      if (leftMap) {
        this.setLabels(leftMap);
      }

      if (rightMap) {
        this.setLabels(rightMap);
      }
    } else {
      this.setLabels(this.map);
    }
  };

  setLabels = (map) => {
    const { basemap, lang, mapLabels } = this.props;

    const LABELS_GROUP = ["labels"];

    // if (map && map.getStyle()) {
    //   const { layers, metadata } = map.getStyle();

    //   const labelGroups = Object.keys(metadata["mapbox:groups"]).filter((k) => {
    //     const { name } = metadata["mapbox:groups"][k];

    //     const matchedGroups = LABELS_GROUP.filter((rgr) =>
    //       name.toLowerCase().includes(rgr)
    //     );

    //     return matchedGroups.some((bool) => bool);
    //   });

    //   const labelsWithMeta = labelGroups.map((_groupId) => ({
    //     ...metadata["mapbox:groups"][_groupId],
    //     id: _groupId,
    //   }));
    //   const labelsToDisplay =
    //     labelsWithMeta.find((_basemap) =>
    //       _basemap.name.includes(basemap?.labelsGroup)
    //     ) || {};

    //   const labelLayers = layers.filter((l) => {
    //     const { metadata: layerMetadata } = l;
    //     if (!layerMetadata) return false;

    //     const gr = layerMetadata["mapbox:group"];
    //     return labelGroups.includes(gr);
    //   });

    //   labelLayers.forEach((_layer) => {
    //     const match = _layer.metadata["mapbox:group"] === labelsToDisplay.id;
    //     map.setLayoutProperty(
    //       _layer.id,
    //       "visibility",
    //       match && mapLabels ? "visible" : "none"
    //     );
    //     map.setLayoutProperty(_layer.id, "text-field", ["get", `name_${lang}`]);
    //   });
    // }

    return true;
  };

  applyRoads = () => {
    const { leftMap, rightMap } = this.state;
    if (!this.map) {
      if (leftMap) {
        this.setRoads(leftMap);
      }

      if (rightMap) {
        this.setRoads(rightMap);
      }
    } else {
      this.setRoads(this.map);
    }
  };

  setRoads = (map) => {
    const ROADS_GROUP = ["roads"];

    if (map && map.getStyle()) {
      const { mapRoads } = this.props;
      const { layers, metadata } = map.getStyle();

      const groups =
        metadata &&
        Object.keys(metadata["mapbox:groups"]).filter((k) => {
          const { name } = metadata["mapbox:groups"][k];
          const roadGroups = ROADS_GROUP.map((rgr) =>
            name?.toLowerCase()?.includes(rgr)
          );

          return roadGroups.some((bool) => bool);
        });

      const roadLayers = layers.filter((l) => {
        const roadMetadata = l.metadata;
        if (!roadMetadata) return false;

        const gr = roadMetadata["mapbox:group"];
        return groups.includes(gr);
      });

      roadLayers.forEach((l) => {
        const visibility = mapRoads ? "visible" : "none";
        map.setLayoutProperty(l.id, "visibility", visibility);
      });
    }
  };

  resetClicks() {
    this.setState({ drawClicks: 0 });
  }

  render() {
    const {
      className,
      mapStyle,
      viewport,
      minZoom,
      maxZoom,
      interactiveLayerIds,
      hoverableLayerIds,
      drawing,
      loading,
      loadingMessage,
      basemap,
      onClickAnalysis,
      onDrawComplete,
      drawingMode,
      comparing,
    } = this.props;

    let tipText;
    if (this.state.drawClicks <= 0) {
      tipText = "Click an origin point to start drawing.";
    } else if (this.state.drawClicks < 3) {
      tipText = "Click to add another point.";
    } else {
      tipText = "Click to add a point or close shape.";
    }

    const mapInteractiveLayerIds = [
      ...interactiveLayerIds,
      ...hoverableLayerIds,
    ];

    const style = {
      position: "absolute",
      top: 0,
      bottom: 0,
      left: 0,
    };

    return (
      <div
        className={cx("c-map", { "no-pointer-events": drawing }, className)}
        style={{ backgroundColor: basemap?.color || basemap?.backgroundColor }}
      >
        {comparing ? (
          <div
            ref={this.mapCompareContainer}
            style={{ ...style, width: "100%" }}
          >
            <RenderMap
              comparing={comparing}
              mapSide="left"
              mapStyle={mapStyle || ""}
              viewport={viewport}
              bounds={this.state.bounds}
              onClick={this.onClick}
              onMouseMove={this.onMouseMove}
              onLoad={this.onLoad}
              attributionControl={false}
              minZoom={minZoom}
              maxZoom={maxZoom}
              style={style}
            />
            <RenderMap
              comparing={comparing}
              mapSide="right"
              mapStyle={mapStyle || ""}
              viewport={viewport}
              bounds={this.state.bounds}
              onClick={this.onClick}
              onMouseMove={this.onMouseMove}
              onLoad={this.onLoad}
              attributionControl={false}
              minZoom={minZoom}
              maxZoom={maxZoom}
              style={style}
            />
          </div>
        ) : (
          <RenderMap
            comparing={comparing}
            mapStyle={mapStyle || ""}
            viewport={viewport}
            bounds={this.state.bounds}
            onViewportChange={this.onViewportChange}
            onClick={this.onClick}
            onMouseMove={this.onMouseMove}
            onLoad={this.onLoad}
            interactiveLayerIds={mapInteractiveLayerIds}
            attributionControl={false}
            minZoom={minZoom}
            maxZoom={maxZoom}
            onClickAnalysis={onClickAnalysis}
            drawing={drawing}
            onDrawComplete={onDrawComplete}
            drawingMode={drawingMode}
          />
        )}

        <Icon className="map-icon-crosshair" icon={iconCrosshair} />
        {loading && (
          <Loader
            className="map-loader"
            theme="theme-loader-light"
            message={loadingMessage}
          />
        )}
      </div>
    );
  }
}

export default MapComponent;
