import React, { PureComponent } from "react";
import PropTypes from "prop-types";
import cx from "classnames";

import Icon from "@/components/ui/icon";

import FilterSection from "./components/filter-section";
import DrawSection from "./components/draw-section";

import settingsIcon from "@/assets/icons/settings.svg?sprite";
import polygonIcon from "@/assets/icons/polygon.svg?sprite";
import boundariesIcon from "@/assets/icons/boundaries.svg?sprite";

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
    setUtilityPanelSettings: PropTypes.func,
    setParamInteractions: PropTypes.func,
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

  handleToggleCollapse = () => {
    const { collapsed, setUtilityPanelSettings } = this.props;
    setUtilityPanelSettings({ collapsed: !collapsed });
  };

  render() {
    const {
      activeTab,
      selectedFilterType,
      hidden,
      collapsed,
      hideHeader,
      className,
      setUtilityActiveTab,
      setSelectedFilterType,
      setParamInteractions,
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
    } = this.props;

    if (hidden) {
      return null;
    }

    return (
      <div className={cx("c-utility-panel", { collapsed, "hide-header": hideHeader }, className)}>
        {!hideHeader && (
          <div className="utility-header" onClick={this.handleToggleCollapse}>
            <Icon icon={settingsIcon} className="utility-icon" />
            <span className="utility-title">UTILITY</span>
          </div>
        )}

        {(!collapsed || hideHeader) && <div className="options">
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
        </div>}

        {(!collapsed || hideHeader) && activeTab === "filter" && (
          <div className="utility-content">
            <FilterSection
              selectedFilterType={selectedFilterType}
              setSelectedFilterType={setSelectedFilterType}
              setParamInteractions={setParamInteractions}
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
      </div>
    );
  }
}

export default UtilityPanel;
