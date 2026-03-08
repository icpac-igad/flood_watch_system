import React, { Component, createRef } from "react";
import classnames from "classnames";
import PropTypes from "prop-types";

import isEqual from "lodash/isEqual";
import isEmpty from "lodash/isEmpty";

import ReactMapGL, { FlyToInterpolator, TRANSITION_EVENTS } from "react-map-gl";

import { easeCubic } from "d3-ease";

import "./styles.scss";

const DEFAULT_VIEWPORT = {
  zoom: 2,
  lat: 0,
  lng: 0,
};

class Map extends Component {
  events = {};

  static propTypes = {
    /** A function that returns the map instance */
    children: PropTypes.func,

    /** Custom css class for styling */
    customClass: PropTypes.string,

    /** An object that defines the viewport
     * @see https://uber.github.io/react-map-gl/#/Documentation/api-reference/interactive-map?section=initialization
     */
    viewport: PropTypes.shape({}),

    /** An object that defines the bounds */
    bounds: PropTypes.shape({
      bbox: PropTypes.array,
      options: PropTypes.shape({}),
    }),

    /** A boolean that allows panning */
    dragPan: PropTypes.bool,

    /** A boolean that allows rotating */
    dragRotate: PropTypes.bool,

    /** A boolean that allows zooming */
    scrollZoom: PropTypes.bool,

    /** A boolean that allows zooming */
    touchZoom: PropTypes.bool,

    /** A boolean that allows touch rotating */
    touchRotate: PropTypes.bool,

    /** A boolean that allows double click zooming */
    doubleClickZoom: PropTypes.bool,

    /** A function that exposes when the map is loaded. It returns and object with the `this.map` and `this.mapContainer` reference. */
    onLoad: PropTypes.func,

    /** A function that exposes the viewport */
    onViewportChange: PropTypes.func,

    /** A function that exposes the viewport */
    getCursor: PropTypes.func,
  };

  static defaultProps = {
    children: null,
    customClass: null,
    viewport: DEFAULT_VIEWPORT,
    bounds: {},
    dragPan: true,
    dragRotate: true,

    onViewportChange: () => {},
    onLoad: () => {},
    getCursor: ({ isHovering, isDragging }) => {
      if (isDragging) return "grabbing";
      if (isHovering) return "pointer";
      return "grab";
    },
  };

  mapRef = createRef();

  mapContainer = createRef();

  state = {
    viewport: {
      ...DEFAULT_VIEWPORT,
      ...this.props.viewport, // eslint-disable-line
    },
    flying: false,
    loaded: false,
  };

  componentDidMount() {
    const { bounds } = this.props;
    const { loaded } = this.state;

    // Only fit bounds if map is loaded and bounds exist
    if (loaded && !isEmpty(bounds) && !!bounds.bbox) {
      this.fitBounds();
    }
  }

  componentDidUpdate(prevProps) {
    const { viewport: prevViewport, bounds: prevBounds } = prevProps;
    const { viewport, bounds } = this.props;
    const { viewport: stateViewport, loaded } = this.state;

    if (!isEqual(viewport, prevViewport)) {
      // eslint-disable-next-line
      this.setState({
        viewport: {
          ...stateViewport,
          ...viewport,
        },
      });
    }

    if (
      loaded &&
      !isEmpty(bounds) &&
      !isEqual(bounds, prevBounds) &&
      !isEmpty(bounds.bbox)
    ) {
      this.fitBounds();
    }
  }

  onError = (evt) => {
    const err = evt?.error || evt;
    console.error('[MapGL onError]', {
      message: err?.message || String(err),
      sourceId: evt?.sourceId,
      source: evt?.source,
      type: evt?.type,
      error: err,
    });
  };

  onLoad = () => {
    const { onLoad, bounds } = this.props;
    // Convert map reference to mapbox map instance before parsing map options
    this.map = this.mapRef.current.getMap();
    this.setState({ loaded: true });

    onLoad({
      map: this.map,
      mapContainer: this.mapContainer,
    });

    // Fit bounds after map loads if bounds were provided
    if (!isEmpty(bounds) && !!bounds.bbox) {
      this.fitBounds();
    }
  };

  onViewportChange = (v) => {
    const { onViewportChange } = this.props;

    this.setState({ viewport: v });
    onViewportChange(v);
  };

  onResize = (v) => {
    const { onViewportChange } = this.props;
    const { viewport } = this.state;
    const newViewport = {
      ...viewport,
      ...v,
    };

    this.setState({ viewport: newViewport });
    onViewportChange(newViewport);
  };

  onMoveEnd = () => {
    const { onViewportChange } = this.props;
    const { viewport } = this.state;

    if (this.map) {
      const bearing = this.map.getBearing();
      const pitch = this.map.getPitch();
      const zoom = this.map.getZoom();
      const { lng, lat } = this.map.getCenter();

      const newViewport = {
        ...viewport,
        bearing,
        pitch,
        zoom,
        latitude: lat,
        longitude: lng,
      };

      // Publish new viewport and save it into the state
      this.setState({ viewport: newViewport });
      onViewportChange(newViewport);
    }
  };

  fitBounds = () => {
    const { bounds, onViewportChange } = this.props;
    const { bbox, options = {} } = bounds;

    // Check if map is ready
    if (!this.map || !this.state.loaded) {
      console.warn('Map not ready for fitBounds');
      return;
    }

    // Validate bbox array format [minLng, minLat, maxLng, maxLat]
    if (!Array.isArray(bbox) || bbox.length !== 4) {
      console.error('Invalid bbox format:', bbox);
      return;
    }

    const [minLng, minLat, maxLng, maxLat] = bbox;

    // Validate coordinates
    if (isNaN(minLng) || isNaN(minLat) || isNaN(maxLng) || isNaN(maxLat)) {
      console.error('Invalid bbox coordinates:', bbox);
      return;
    }

    if (minLng >= maxLng || minLat >= maxLat) {
      console.error('Invalid bbox bounds (min >= max):', bbox);
      return;
    }

    try {
      // Set flying state to disable interactions during transition
      this.setState({ flying: true });

      // Listen for moveend event to sync viewport when transition completes
      const handleMoveEnd = () => {
        if (this.map) {
          const bearing = this.map.getBearing();
          const pitch = this.map.getPitch();
          const zoom = this.map.getZoom();
          const { lng, lat } = this.map.getCenter();

          const newViewport = {
            ...this.state.viewport,
            bearing,
            pitch,
            zoom,
            latitude: lat,
            longitude: lng,
            transitionDuration: 0, // Prevent another transition
          };

          // Update both local state and Redux store
          this.setState({ viewport: newViewport, flying: false });
          onViewportChange(newViewport);
        }

        // Remove the event listener after handling
        this.map.off('moveend', handleMoveEnd);
      };

      // Attach the moveend listener
      this.map.once('moveend', handleMoveEnd);

      // Use MapLibre's native fitBounds API
      this.map.fitBounds(
        [[minLng, minLat], [maxLng, maxLat]],
        {
          padding: options.padding || 50,
          duration: 2500,
          animate: true,
          ...options
        }
      );
    } catch (err) {
      console.error('Error fitting bounds:', err);
      this.setState({ flying: false });
    }
  };

  render() {
    const {
      customClass,
      children,
      getCursor,
      dragPan,
      dragRotate,
      scrollZoom,
      touchZoom,
      touchRotate,
      doubleClickZoom,
      comparing,
      ...mapboxProps
    } = this.props;
    const { viewport, loaded, flying } = this.state;

    return (
      <div
        ref={this.mapContainer}
        className={classnames({
          "c-mapbox-map": !comparing,
          [customClass]: !!customClass,
        })}
      >
        <ReactMapGL
          ref={this.mapRef}
          // CUSTOM PROPS FROM REACT MAPBOX API
          {...mapboxProps}
          // VIEWPORT
          {...viewport}
          width="100%"
          height="100%"
          // INTERACTIVE
          dragPan={!flying && dragPan}
          dragRotate={!flying && dragRotate}
          scrollZoom={!flying && scrollZoom}
          touchZoom={!flying && touchZoom}
          touchRotate={!flying && touchRotate}
          doubleClickZoom={!flying && doubleClickZoom}
          // DEFAULT FUNC IMPLEMENTATIONS
          onViewportChange={this.onViewportChange}
          onResize={this.onResize}
          onLoad={this.onLoad}
          onError={this.onError}
          getCursor={getCursor}
          transitionInterpolator={new FlyToInterpolator()}
          transitionEasing={easeCubic}
          preventStyleDiffing
          disableTokenWarning={true}
        >
          {loaded &&
            !!this.map &&
            typeof children === "function" &&
            children(this.map)}
        </ReactMapGL>
      </div>
    );
  }
}

export default Map;
