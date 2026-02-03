import React, { PureComponent, Fragment } from "react";
import PropTypes from "prop-types";
import Dropzone from "react-dropzone";
import cx from "classnames";
import { format } from "d3-format";

import Button from "@/components/ui/button";
import Icon from "@/components/ui/icon";
import DrawingModeSelector from "@/components/analysis/components/chose-analysis/drawing-mode-selector/component";
import UploadShapeModal from "@/components/analysis/components/chose-analysis/upload-shape-modal";

import { trackEvent } from "@/utils/analytics";

import closeIcon from "@/assets/icons/close.svg?sprite";
import infoIcon from "@/assets/icons/info.svg?sprite";
import polygonIcon from "@/assets/icons/polygon.svg?sprite";
import rectangleIcon from "@/assets/icons/draw_rectangle.svg?sprite";

import "./styles.scss";

class DrawSection extends PureComponent {
  static propTypes = {
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

  state = {
    uploadModalOpen: false,
  };

  render() {
    const {
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

    const hasError = error && errorMessage;

    const drawingModes = [
      { label: "Polygon", value: "draw_polygon", icon: polygonIcon },
      { label: "Rectangle", value: "draw_rectangle", icon: rectangleIcon },
    ];

    return (
      <div className="c-draw-section">
        <div className="draw-menu-title">
          Draw in the map the area you want to analyze
        </div>
        <DrawingModeSelector
          options={drawingModes}
          activeMode={drawingMode}
          onChange={(mode) => {
            setMapSettings({ drawingMode: mode });
          }}
        />
        <Button
          className="draw-menu-button"
          theme={drawing ? "theme-button-light wide" : "wide"}
          onClick={() => {
            setMapSettings({ drawing: !drawing });
            if (!drawing) {
              setMenuSettings({ menuSection: "" });
            }
            trackEvent({
              category: "Map analysis",
              action: "User drawn shape",
              label: drawing ? "Cancel" : "Start",
            });
          }}
        >
          {drawing ? "CANCEL" : "START DRAWING"}
        </Button>
        <div className="draw-menu-separator">or</div>
        <Dropzone
          className={cx(
            "draw-menu-input",
            { error: error && errorMessage },
            { uploading }
          )}
          onDropAccepted={onDropAccepted}
          onDropRejected={onDropRejected}
          maxSize={uploadConfig.sizeLimit}
          accept={uploadConfig.types}
          multiple={false}
          disabled={uploading}
        >
          {hasError && !uploading && (
            <Fragment>
              <p className="error-title">{error}</p>
              <p className="small-text error-desc">{errorMessage}</p>
            </Fragment>
          )}
          {!hasError && !uploading && (
            <Fragment>
              <p>
                Drag and drop your <b>polygon data file</b> or click here to
                upload
              </p>
              <p className="small-text">{"Recommended file size < 1 MB"}</p>
            </Fragment>
          )}
          {!hasError && uploading && (
            <div className="uploading-shape">
              <p className="file-name">{file && file.name}</p>
              <p className="file-size">
                {`Uploading ${(file && format(".2s")(file.size)) || 0}B`}
              </p>
              <div className="upload-bar">
                <div className="loading-bar">
                  <span className="full-bar" />
                  <span
                    className="status-bar"
                    style={{ width: `${uploadStatus || 0}%` }}
                  />
                </div>
                <Button
                  theme="theme-button-clear"
                  className="cancel-upload-btn"
                  onClick={handleCancelUpload}
                >
                  <Icon className="cancel-upload-icon" icon={closeIcon} />
                </Button>
              </div>
            </div>
          )}
        </Dropzone>
        <div className="terms">
          <div className="first-term">
            <p>Learn more about supported file formats</p>
            <Button
              className="info-button"
              theme="theme-button-tiny square"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                this.setState({ uploadModalOpen: true });
              }}
            >
              <Icon icon={infoIcon} className="info-icon" />
            </Button>
          </div>
          {termsOfServicePageUrl && (
            <p>
              By uploading data you agree to the{" "}
              <a
                href={termsOfServicePageUrl}
                target="_blank"
                rel="noopenner nofollower"
              >
                Terms of Service
              </a>
            </p>
          )}
        </div>
        <UploadShapeModal
          open={this.state.uploadModalOpen}
          onRequestClose={() => this.setState({ uploadModalOpen: false })}
        />
      </div>
    );
  }
}

export default DrawSection;
