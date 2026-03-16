import React, { PureComponent } from "react";
import PropTypes from "prop-types";
import { connect } from "react-redux";
import cx from "classnames";

import Icon from "@/components/ui/icon";
import BasemapButton from "@/components/basemaps/basemap-button";
import { getBasemapsProps } from "@/components/basemaps/selectors";
import * as mapActions from "@/components/map/actions";
import { trackEvent } from "@/utils/analytics";

import layersIcon from "@/assets/icons/layers.svg?sprite";

import "./styles.scss";

class BasemapPanel extends PureComponent {
  static propTypes = {
    basemaps: PropTypes.object,
    activeBasemap: PropTypes.object,
    setMapSettings: PropTypes.func,
  };

  state = {
    collapsed: true,
  };

  handleToggle = () => {
    this.setState((prev) => ({ collapsed: !prev.collapsed }));
  };

  selectBasemap = ({ value } = {}) => {
    const { setMapSettings } = this.props;
    setMapSettings({ basemap: { value } });
    trackEvent({
      category: "Map data",
      action: "basemap changed",
      label: value,
    });
  };

  render() {
    const { basemaps, activeBasemap } = this.props;
    const { collapsed } = this.state;

    return (
      <div className={cx("c-basemap-panel", { collapsed })}>
        <div className="basemap-header" onClick={this.handleToggle}>
          <Icon icon={layersIcon} className="basemap-icon" />
          <span className="basemap-title">BASEMAP</span>
        </div>
        {!collapsed && basemaps && (
          <div className="basemap-body">
            <div className="basemap-grid">
              {Object.values(basemaps).map((item) => (
                <div key={item.value} className="basemap-col">
                  <BasemapButton
                    {...item}
                    active={activeBasemap?.value === item?.value}
                    onSelectBasemap={this.selectBasemap}
                  />
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }
}

const mapStateToProps = (state) => ({
  ...getBasemapsProps(state),
});

export default connect(mapStateToProps, mapActions)(BasemapPanel);
