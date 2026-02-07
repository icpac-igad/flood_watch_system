import { createElement, PureComponent } from "react";
import { connect } from "react-redux";
import PropTypes from "prop-types";

import reducerRegistry from "@/redux/registry";

import Component from "./component";

import * as ownActions from "./actions";
import * as mapActions from "@/components/map/actions";
import * as menuActions from "@/components/map-menu/actions";
import * as analysisActions from "@/components/analysis/actions";

import reducers, { initialState } from "./reducers";
import { cancelToken } from "@/utils/request";
import uploadConfig from "@/components/analysis/upload-config.json";

import { getUtilityPanelProps } from "./selectors";
import { getChooseAnalysisProps } from "@/components/analysis/components/chose-analysis/selectors";

const actions = {
  ...ownActions,
  ...mapActions,
  ...menuActions,
  ...analysisActions,
};

class UtilityPanelContainer extends PureComponent {
  static propTypes = {
    setMapSettings: PropTypes.func,
    uploadShape: PropTypes.func,
    setAnalysisLoading: PropTypes.func,
  };

  state = {
    uploadStatus: 0,
    file: null,
  };

  handleCheckUpload = (e) => {
    this.setState({ uploadStatus: (e.loaded / e.total) * 25 });
  };

  handleCheckDownload = (e) => {
    this.setState({
      uploadStatus: 25 + (e.loaded / e.total) * 25,
    });
  };

  handleGeostoreUpload = (e) => {
    this.setState({
      uploadStatus: 50 + (e.loaded / e.total) * 25,
    });
  };

  handleGeostoreDownload = (e) => {
    this.setState({
      uploadStatus: 75 + (e.loaded / e.total) * 25,
    });
  };

  onDropAccepted = (files) => {
    const file = files && files[0];
    this.setState({ file, uploadStatus: 0 });
    this.handleUploadShape(file);
  };

  onDropRejected = (files) => {
    const { setAnalysisLoading } = this.props;
    const file = files && files[0];

    if (files && file && files.length > 1) {
      setAnalysisLoading({
        error: "Multiple files not supported",
        errorMessage:
          "Only single files of type .zip, .csv, .json, .geojson, .kml and .kmz fles are supported.",
      });
    } else if (file && !uploadConfig.types.includes(file.type)) {
      setAnalysisLoading({
        error: "Invalid file type",
        errorMessage:
          "Only .zip, .csv, .json, .geojson, .kml and .kmz fles are supported.",
      });
    } else if (file && file.size > uploadConfig.sizeLimit) {
      setAnalysisLoading({
        error: "File too large",
        errorMessage:
          "The recommended maximum fle size is 1MB. Anything larger than that may not work properly.",
      });
    } else {
      setAnalysisLoading({
        error: "Error attaching file",
        errorMessage: "Please contact us for support.",
      });
    }
  };

  handleUploadShape = (file) => {
    if (this.uploadShape) {
      this.uploadShape.cancel();
    }
    this.uploadShape = cancelToken();
    this.props.uploadShape({
      shape: file,
      onCheckUpload: this.handleCheckUpload,
      onCheckDownload: this.handleCheckDownload,
      onGeostoreUpload: this.handleGeostoreUpload,
      onGeostoreDownload: this.handleGeostoreDownload,
      token: this.uploadShape.token,
    });
  };

  handleCancelUpload = () => {
    const { setAnalysisLoading } = this.props;
    if (this.uploadShape) {
      this.uploadShape.cancel("cancel upload shape");
    }
    setAnalysisLoading({
      uploading: false,
      loading: false,
      error: "",
      errorMessage: "",
    });
  };

  render() {
    return createElement(Component, {
      ...this.props,
      ...this.state,
      onDropAccepted: this.onDropAccepted,
      onDropRejected: this.onDropRejected,
      handleCancelUpload: this.handleCancelUpload,
      uploadConfig,
    });
  }
}

const mapStateToProps = (state) => ({
  ...getUtilityPanelProps(state),
  ...getChooseAnalysisProps(state),
});

reducerRegistry.registerModule("utilityPanel", {
  actions: ownActions,
  reducers,
  initialState,
});

export default connect(mapStateToProps, actions)(UtilityPanelContainer);
