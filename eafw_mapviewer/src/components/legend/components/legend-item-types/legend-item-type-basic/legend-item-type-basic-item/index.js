import React from "react";
import PropTypes from "prop-types";

import Icon from "@/components/ui/icon";

import "./styles.scss";

class LegendItem extends React.PureComponent {
  static propTypes = {
    size: PropTypes.number,
    color: PropTypes.string,
    name: PropTypes.string,
    icon: PropTypes.string, // triangle, circle, square, line
    hideIcon: PropTypes.bool,
    iconSource: PropTypes.string,
    iconWidth: PropTypes.number,
    iconHeight: PropTypes.number,
  };

  static defaultProps = {
    size: 12,
    color: "transparent",
    name: "",
    icon: "square",
    hideIcon: false,
    iconSource: "url",
    iconWidth: null,
    iconHeight: null,
  };

  getIconHtml = (iconName) => {
    const { name, hideIcon, color, size, icon, iconSource, iconWidth, iconHeight } = this.props;

    if (hideIcon) {
      return null;
    }

    if (iconName === "triangle") {
      return (
        <div
          className={`icon-${icon}`}
          style={{
            boderRightWidth: size / 2,
            boderLeftWidth: size / 2,
            boderBottomWidth: size,
            borderBottomColor: color,
          }}
        />
      );
    }

    if (iconName === "line") {
      return (
        <div
          className={`icon-${icon}`}
          style={{ width: size, backgroundColor: color }}
        />
      );
    }

    if (iconName === "square" || iconName === "circle") {
      return (
        <div
          className={`icon-${icon}`}
          style={{ width: size, height: size, backgroundColor: color }}
        />
      );
    }

    if (iconSource === "sprite") {
      const style = {};

      if (color) {
        style.fill = color;
      }

      return (
        <div className="custom-icon">
          <Icon icon={`icon-${icon}`} style={{ ...style }} />
        </div>
      );
    }

    const customIconStyle = {};
    if (iconWidth) customIconStyle.width = `${iconWidth}px`;
    if (iconHeight) customIconStyle.height = `${iconHeight}px`;

    return (
      <div className="custom-icon" style={customIconStyle}>
        <img src={icon} alt={name} style={{ width: "100%", height: "100%" }} />
      </div>
    );
  };

  render() {
    const { name, icon } = this.props;

    return (
      <div className="c-legend-item-basic">
        {this.getIconHtml(icon)}

        <span className="name">{name}</span>
      </div>
    );
  }
}

export default LegendItem;
