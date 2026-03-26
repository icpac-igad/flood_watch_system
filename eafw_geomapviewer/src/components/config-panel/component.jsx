import React, { PureComponent } from "react";
import PropTypes from "prop-types";
import cx from "classnames";

import Icon from "@/components/ui/icon";

import settingsIcon from "@/assets/icons/settings.svg?sprite";

import "./styles.scss";

class ConfigPanel extends PureComponent {
  static propTypes = {
    className: PropTypes.string,
    children: PropTypes.node,
  };

  state = { collapsed: false };

  handleToggleCollapse = () => {
    this.setState((prev) => ({ collapsed: !prev.collapsed }));
  };

  render() {
    const { className, children } = this.props;
    const { collapsed } = this.state;

    return (
      <div className={cx("c-config-panel", { collapsed }, className)}>
        <div className="config-header" onClick={this.handleToggleCollapse}>
          <Icon icon={settingsIcon} className="config-icon" />
          <span className="config-title">CONFIG</span>
        </div>
        {!collapsed && (
          <div className="config-content">{children}</div>
        )}
      </div>
    );
  }
}

export default ConfigPanel;
