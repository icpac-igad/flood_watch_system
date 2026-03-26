import React, { PureComponent } from "react";
import PropTypes from "prop-types";
import cx from "classnames";

import Icon from "@/components/ui/icon";

import FilterSection from "./components/filter-section";
import DrawSection from "./components/draw-section";

import settingsIcon from "@/assets/icons/settings.svg?sprite";
import polygonIcon from "@/assets/icons/polygon.svg?sprite";
import boundariesIcon from "@/assets/icons/boundaries.svg?sprite";
import layersIcon from "@/assets/icons/layers.svg?sprite";

import "./styles.scss";

class UtilityPanel extends PureComponent {
  static propTypes = {
    activeTab: PropTypes.string,
    selectedFilterType: PropTypes.string,
    hidden: PropTypes.bool,
    collapsed: PropTypes.bool,
    hideHeader: PropTypes.bool,
    className: PropTypes.string,
    setUtilityActiveTab: PropTypes.func,
    setSelectedFilterType: PropTypes.func,
    configContent: PropTypes.node,
    // Drawing props
    drawing: PropTypes.bool,
    drawingMode: PropTypes.string,
    setMapSettings: PropTypes.func,
    setMenuSettings: PropTypes.func,
    onDropAccepted: PropTypes.func,
    onDropRejected: PropTypes.func,
    handleCancelUpload: PropTypes.func,
    uploadConfig: PropTypes.object,
    uploading: PropTypes.bool,
    uploadStatus: PropTypes.number,
    file: PropTypes.object,
    error: PropTypes.string,
    errorMessage: PropTypes.string,
    termsOfServicePageUrl: PropTypes.string,
  };

  state = { panelTab: "utility", collapsed: true };

  setPanelTab = (tab) => {
    this.setState((prev) => ({
      panelTab: tab,
      // clicking the active tab toggles; clicking a different tab always opens
      collapsed: prev.panelTab === tab ? !prev.collapsed : false,
    }));
  };

  render() {
    const {
      activeTab,
      selectedFilterType,
      hidden,
      hideHeader,
      className,
      setUtilityActiveTab,
      setSelectedFilterType,
      drawing,
      drawingMode,
      setMapSettings,
      setMenuSettings,
      onDropAccepted,
      onDropRejected,
      handleCancelUpload,
      uploadConfig,
      uploading,
      uploadStatus,
      file,
      error,
      errorMessage,
      termsOfServicePageUrl,
      configContent,
    } = this.props;

    const { panelTab, collapsed } = this.state;

    if (hidden) {
      return null;
    }

    return (
      <div className={cx("c-utility-panel", { "hide-header": hideHeader, collapsed: collapsed && !hideHeader }, className)}>
        {!hideHeader && (
          <div className="panel-tabs">
            <div
              className={cx("panel-tab", { active: panelTab === "utility" })}
              onClick={() => this.setPanelTab("utility")}
            >
              <Icon icon={settingsIcon} className="panel-tab-icon" />
              <span className="panel-tab-title">FILTERS</span>
            </div>
            {configContent && (
              <div
                className={cx("panel-tab", { active: panelTab === "config" })}
                onClick={() => this.setPanelTab("config")}
              >
                <Icon icon={layersIcon} className="panel-tab-icon" />
                <span className="panel-tab-title">MAPSTYLES</span>
              </div>
            )}
          </div>
        )}

        {/* UTILITY tab */}
        {panelTab === "utility" && (
          <>
            {(!collapsed || hideHeader) && (
              <div className="options">
                <button
                  className={cx({ selected: activeTab === "filter" })}
                  onClick={() => setUtilityActiveTab("filter")}
                >
                  <div className="button-wrapper">
                    <Icon icon={boundariesIcon} className="icon-filter" />
                    <div className="label">FILTER</div>
                  </div>
                </button>
                <button
                  className={cx("draw-upload-tab", { selected: activeTab === "draw" })}
                  onClick={() => setUtilityActiveTab("draw")}
                >
                  <div className="button-wrapper">
                    <Icon icon={polygonIcon} className="icon-polygon" />
                    <div className="label">DRAW OR UPLOAD SHAPE</div>
                  </div>
                </button>
              </div>
            )}

            {(!collapsed || hideHeader) && activeTab === "filter" && (
              <div className="utility-content">
                <FilterSection
                  selectedFilterType={selectedFilterType}
                  setSelectedFilterType={setSelectedFilterType}
                />
              </div>
            )}

            {(!collapsed || hideHeader) && activeTab === "draw" && (
              <div className="utility-content">
                <DrawSection
                  drawing={drawing}
                  drawingMode={drawingMode}
                  setMapSettings={setMapSettings}
                  setMenuSettings={setMenuSettings}
                  onDropAccepted={onDropAccepted}
                  onDropRejected={onDropRejected}
                  handleCancelUpload={handleCancelUpload}
                  uploadConfig={uploadConfig}
                  uploading={uploading}
                  uploadStatus={uploadStatus}
                  file={file}
                  error={error}
                  errorMessage={errorMessage}
                  termsOfServicePageUrl={termsOfServicePageUrl}
                />
              </div>
            )}
          </>
        )}

        {/* CONFIG tab */}
        {panelTab === "config" && configContent && (
          <div className="config-content">
            {configContent}
          </div>
        )}
      </div>
    );
  }
}

export default UtilityPanel;
