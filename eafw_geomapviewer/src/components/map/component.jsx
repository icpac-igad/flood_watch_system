import React, { Component, PureComponent, createRef } from "react";
import PropTypes from "prop-types";
import isEqual from "lodash/isEqual";
import isEmpty from "lodash/isEmpty";
import debounce from "lodash/debounce";
import cx from "classnames";

import { trackMapLatLon, trackEvent } from "@/utils/analytics";

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
// import { pulsingDot } from "./mapImages";

import mapStyleForNoStyle from "./style";

const EXTERNAL_BASEMAP_SOURCE_ID = "__external-basemap-source";
const EXTERNAL_BASEMAP_LAYER_ID = "__external-basemap-layer";

// Styles
import "./styles.scss";

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
    mapLoaded: false,
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
      initialBbox,
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
      initialBbox: prevInitialBbox,
      vectorLayerIcons: prevVectorLayerIcons,
    } = prevProps;

    if (!drawing && prevDrawing) {
      this.resetClicks();
    }

    if (drawing && !prevDrawing) {
      clearMapInteractions();
    }

    if (
      basemap?.value !== prevBasemap?.value ||
      basemap?.basemapGroup !== prevBasemap?.basemapGroup
    ) {
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

    // Apply initialBbox once map is loaded and the bbox arrives from datasets
    if (this.state.mapLoaded && initialBbox && !prevInitialBbox) {
      this.applyInitialBbox();
    }

    if (!isEqual(vectorLayerIcons, prevVectorLayerIcons)) {
      this.loadMapImages();
    }
  }

  componentWillUnmount() {
    if (this.map) {
      this.map.off("style.load", this.onStyleLoad);
    }
    if (this.state.compareMap) {
      this.state.compareMap.remove();
    }
  }

  loadMapImages = async () => {
    const { vectorLayerIcons } = this.props;

    if (vectorLayerIcons && !!vectorLayerIcons.length && this.map) {
      vectorLayerIcons.forEach((icon) => {
        this.map.loadImage(icon.url, (error, iconImage) => {
          if (!error && iconImage) {
            this.map.addImage(icon.name, iconImage);
          }
        });
      });
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

  applyInitialBbox = () => {
    const { initialBbox, setMapSettings, setInitialBbox } = this.props;
    if (initialBbox && initialBbox.length) {
      this.setState({ bounds: { bbox: initialBbox, options: { padding: 50 } } });
      setMapSettings({ canBound: false });
      setInitialBbox(null);
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
      this.setState({ mapLoaded: true }, () => {
        const { initialBbox } = this.props;
        if (initialBbox) {
          this.applyInitialBbox();
        }
      });

      this.fitMapBoundaryBounds();

      // Listeners
      this.map.on("style.load", this.onStyleLoad);
    }

    this.loadMapImages();

    // add images

    // map.addImage("pulsing-dot", pulsingDot, { pixelRatio: 2 });
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
          this.map.queryRenderedFeatures(e.point, {
            layers: hoverableLayerIds,
          });
        if (features && !!features.length) {
          const { lngLat } = e;

          setMapHoverInteraction({ feature: features[0], lngLat });
        } else {
          hasHoverFeature && clearMapHoverInteraction();
        }
      } catch {
        // Layer may not exist yet after a style change
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

    try {
      const style = map && map.getStyle();
      if (!style) return false;

      const { layers = [], metadata = {} } = style;
      const mapboxGroups = metadata["mapbox:groups"] || {};

      const basemapGroups = Object.keys(mapboxGroups).filter((k) => {
        const { name } = mapboxGroups[k] || {};
        return BASEMAP_GROUPS.some((g) => name?.toLowerCase()?.includes(g));
      });

      const basemapLayers = layers.filter((l) => {
        const { metadata: layerMetadata } = l;
        if (!layerMetadata) return false;
        const gr = layerMetadata["mapbox:group"];
        return basemapGroups.includes(gr);
      });

      // URL-based basemaps: inject as raster layer at the bottom of the style
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
          paint: { "raster-opacity": 1 },
        };

        const firstLayerId = layers.find(
          (l) => l.id !== EXTERNAL_BASEMAP_LAYER_ID
        )?.id;
        if (firstLayerId && map.getLayer(firstLayerId)) {
          map.addLayer(externalLayer, firstLayerId);
        } else {
          map.addLayer(externalLayer);
        }

        return true;
      }

      // Style-based basemaps: remove any external raster and toggle layer group visibility
      removeExternalBasemap();

      // No basemap selected — restore all style basemap layers to visible (default state)
      if (!basemap?.basemapGroup) {
        basemapLayers.forEach((_layer) => {
          if (map.getLayer(_layer.id)) {
            map.setLayoutProperty(_layer.id, "visibility", "visible");
          }
        });
        return true;
      }

      const basemapsWithMeta = basemapGroups.map((_groupId) => ({
        ...mapboxGroups[_groupId],
        id: _groupId,
      }));
      const basemapToDisplay = basemapsWithMeta.find((_basemap) =>
        _basemap?.name?.includes(basemap?.basemapGroup)
      );

      if (!basemapToDisplay) return false;

      basemapLayers.forEach((_layer) => {
        const match = _layer.metadata["mapbox:group"] === basemapToDisplay.id;
        if (map.getLayer(_layer.id)) {
          map.setLayoutProperty(
            _layer.id,
            "visibility",
            match ? "visible" : "none"
          );
        }
      });
    } catch (e) {
      return false;
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
    const { mapLabels } = this.props;

    const LABELS_GROUP = ["labels"];

    try {
      const style = map && map.getStyle();
      if (!style) return;

      const { layers, metadata } = style;
      const mapboxGroups = metadata?.["mapbox:groups"] || {};

      const labelGroupIds = Object.keys(mapboxGroups).filter((k) => {
        const { name } = mapboxGroups[k] || {};
        return LABELS_GROUP.some((g) => name?.toLowerCase()?.includes(g));
      });

      const labelLayers = layers.filter((l) => {
        const { metadata: layerMetadata } = l;
        if (!layerMetadata) return false;
        return labelGroupIds.includes(layerMetadata["mapbox:group"]);
      });

      labelLayers.forEach((_layer) => {
        if (map.getLayer(_layer.id)) {
          map.setLayoutProperty(
            _layer.id,
            "visibility",
            mapLabels ? "visible" : "none"
          );
        }
      });
    } catch (e) {
      return false;
    }

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

    try {
      const style = map && map.getStyle();
      if (!style) return;

      const { mapRoads } = this.props;
      const { layers, metadata } = style;

      const groups =
        metadata?.["mapbox:groups"] &&
        Object.keys(metadata["mapbox:groups"]).filter((k) => {
          const { name } = metadata["mapbox:groups"][k];
          const roadGroups = ROADS_GROUP.map((rgr) =>
            name?.toLowerCase()?.includes(rgr)
          );

          return roadGroups.some((bool) => bool);
        });

      if (!groups) return;

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
    } catch (e) {
      // ignore style-not-loaded errors
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

    // Filter interactive layer IDs to only include layers that exist on the map.
    // After a style change, previously added layers are removed and referencing
    // them in queryRenderedFeatures causes maplibre to throw.
    let mapInteractiveLayerIds = [
      ...interactiveLayerIds,
      ...hoverableLayerIds,
    ];

    if (this.map) {
      try {
        const styleLayers = this.map.getStyle()?.layers;
        if (styleLayers) {
          const existingIds = new Set(styleLayers.map((l) => l.id));
          mapInteractiveLayerIds = mapInteractiveLayerIds.filter((id) =>
            existingIds.has(id)
          );
        } else {
          mapInteractiveLayerIds = [];
        }
      } catch {
        mapInteractiveLayerIds = [];
      }
    }

    const style = {
      position: "absolute",
      top: 0,
      bottom: 0,
      left: 0,
    };

    return (
      <div
        className={cx("c-map", { "no-pointer-events": drawing }, className)}
        style={{ backgroundColor: basemap && basemap.color }}
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
