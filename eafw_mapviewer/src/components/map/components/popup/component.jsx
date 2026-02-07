import React, { Component } from "react";
import PropTypes from "prop-types";
import isEmpty from "lodash/isEmpty";
import isEqual from "lodash/isEqual";
import { Popup as MapPopup } from "react-map-gl";

import Dropdown from "@/components/ui/dropdown";

import AreaSentence from "./components/area-sentence";
import ArticleCard from "./components/article-card";
import CapAlertCard from "./components/cap-alert-card";
import DataTable from "./components/data-table";
import BoundarySentence from "./components/boundary-sentence";
import ContextualSentence from "./components/contextual-sentence";
import PointSentence from "./components/point-sentence";

class Popup extends Component {
  static propTypes = {
    showPopup: PropTypes.bool,
    isDashboard: PropTypes.bool,
    clearMapInteractions: PropTypes.func,
    setMapInteractionSelected: PropTypes.func,
    latitude: PropTypes.number,
    longitude: PropTypes.number,
    selected: PropTypes.object,
    interactionsOptions: PropTypes.array,
    interactionOptionSelected: PropTypes.object,
    activeDatasets: PropTypes.array,
    onClickAnalysis: PropTypes.func,
    map: PropTypes.object,
  };

  state = {
    useClickedPoint: false,
    popupDragOffset: { x: 0, y: 0 },
    popupDragging: false,
    popupDragStart: { x: 0, y: 0 },
  };

  componentDidUpdate(prevProps) {
    const { interactionsOptions, activeDatasets } = this.props;

    if (
      isEmpty(interactionsOptions) &&
      !isEqual(activeDatasets?.length, prevProps.activeDatasets?.length)
    ) {
      this.handleClose();
    }

    if (this.props.showPopup && !prevProps.showPopup) {
      this.setState({ popupDragOffset: { x: 0, y: 0 } });
    }
  }

  handleClickAction = (selected) => {
    const { longitude, latitude, onClickAnalysis } = this.props;
    const { useClickedPoint } = this.state;

    if (useClickedPoint) {
      onClickAnalysis({
        isPoint: true,
        latlng: { lat: latitude, lng: longitude },
      });
    } else {
      const { data, layer, geometry } = selected;
      const { gid } = data || {};
      const { analysisEndpoint, tableName } = layer || {};

      const isAdmin = analysisEndpoint === "admin";
      const isUse = gid && tableName;

      onClickAnalysis({
        data,
        layer,
        geometry,
        isUse,
        isAdmin,
      });
    }

    this.handleClose();
  };

  handlePopupClose = () => {
    this.setState({ useClickedPoint: false });
    this.props.clearMapInteractions();
  };

  // when clicking popup action the map triggers the interaction event
  // causing the popup to open again. this stops it for now.
  handleClose = () => {
    setTimeout(() => this.props.clearMapInteractions(), 300);
  };

  handlePopupDragStart = (e) => {
    e.preventDefault();

    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;

    this.setState((prev) => ({
      popupDragging: true,
      popupDragStart: {
        x: clientX - prev.popupDragOffset.x,
        y: clientY - prev.popupDragOffset.y,
      },
    }));

    window.addEventListener("mousemove", this.handlePopupDragMove);
    window.addEventListener("mouseup", this.handlePopupDragEnd);
    window.addEventListener("touchmove", this.handlePopupDragMove, { passive: false });
    window.addEventListener("touchend", this.handlePopupDragEnd);
  };

  handlePopupDragMove = (e) => {
    if (!this.state.popupDragging) return;

    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;

    this.setState((prev) => ({
      popupDragOffset: {
        x: clientX - prev.popupDragStart.x,
        y: clientY - prev.popupDragStart.y,
      },
    }));
  };

  handlePopupDragEnd = () => {
    this.setState({ popupDragging: false });
    window.removeEventListener("mousemove", this.handlePopupDragMove);
    window.removeEventListener("mouseup", this.handlePopupDragEnd);
    window.removeEventListener("touchmove", this.handlePopupDragMove);
    window.removeEventListener("touchend", this.handlePopupDragEnd);
  };

  handleInteractionChange = (selected) => {
    const { setMapInteractionSelected } = this.props;

    if (selected === "map-clicked-point") {
      this.setState({ useClickedPoint: true });
    } else {
      this.setState({ useClickedPoint: false });
      setMapInteractionSelected(selected);
    }
  };

  renderPopupBody = () => {
    const {
      selected,
      interactionOptionSelected,
      interactionsOptions,
      latitude,
      longitude,
      map,
    } = this.props;

    const { useClickedPoint } = this.state;

    if (selected?.isCapAlert) {
      return <CapAlertCard data={selected} />;
    }

    if (selected?.isArticle) {
      return <ArticleCard data={selected} />;
    }

    const interactionOptionsWithMapPoint = [
      ...interactionsOptions,
      ...[{ label: "Clicked Point", value: "map-clicked-point" }],
    ];

    const hasManyInteractions = interactionOptionsWithMapPoint?.length > 1;

    const { isAoi, isBoundary, isPoint, isLayer } = selected || {};

    return (
      <div className="popup-body">
        {hasManyInteractions && (
          <Dropdown
            className="layer-selector"
            theme="theme-dropdown-native"
            value={
              useClickedPoint ? "map-clicked-point" : interactionOptionSelected
            }
            options={interactionOptionsWithMapPoint}
            onChange={this.handleInteractionChange}
            native
          />
        )}
        {interactionOptionSelected?.label && !hasManyInteractions && (
          <div className="title">{interactionOptionSelected.label}</div>
        )}

        {useClickedPoint ? (
          <PointSentence
            onAnalyze={this.handleClickAction}
            lat={latitude}
            lon={longitude}
          />
        ) : (
          <>
            {isBoundary && (
              <BoundarySentence
                data={selected}
                onAnalyze={() => this.handleClickAction(selected)}
              />
            )}
            {isAoi && <AreaSentence data={selected} />}
            {!isBoundary && !isAoi && isLayer && (
              <DataTable
                selected={selected}
                map={map}
                onClose={this.handleClose}
                onAnalyze={() => this.handleClickAction(selected)}
                isPoint={isPoint}
                popupLat={latitude}
                popupLon={longitude}
                onPopupDragStart={this.handlePopupDragStart}
              />
            )}
            {isPoint && !isLayer && (
              <ContextualSentence
                data={selected}
                latitude={latitude}
                longitude={longitude}
              />
            )}
          </>
        )}
      </div>
    );
  };

  render() {
    const {
      showPopup,
      latitude,
      longitude,
      clearMapInteractions,
      selected,
      isDashboard,
    } = this.props;
    const { popupDragOffset } = this.state;
    const { isBoundary } = selected || {};

    // confirm if the selected layer has interactionConfig setup
    if (selected && selected.layer && !selected.layer.interactionConfig) {
      return null;
    }

    if (showPopup && isBoundary && isDashboard) return null;

    return showPopup ? (
      <MapPopup
        latitude={latitude}
        longitude={longitude}
        onClose={this.handlePopupClose}
        closeOnClick={false}
      >
        <div
          className="c-popup"
          style={{ transform: `translate(${popupDragOffset.x}px, ${popupDragOffset.y}px)` }}
        >
          {this.renderPopupBody()}
        </div>
      </MapPopup>
    ) : null;
  }
}

export default Popup;
