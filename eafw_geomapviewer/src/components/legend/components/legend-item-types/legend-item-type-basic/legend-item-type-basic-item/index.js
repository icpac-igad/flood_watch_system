import React from "react";
import PropTypes from "prop-types";

import Icon from "@/components/ui/icon";

import "./styles.scss";

const RISK_LABEL_MAP = {
  emergency: "Extreme",
  alarm: "Severe",
  warning: "Moderate",
  normal: "Normal",
};

const RISK_COLOR_MAP = {
  normal: "#b0b0b0",
};

const getLegendRiskKey = (value) => {
  const name = String(value || "").trim();
  if (!name) return "";

  return name.split(/\s+/, 1)[0].replace(/[^a-z]/gi, "").toLowerCase();
};

const normalizeLegendName = (value) => {
  const name = String(value || "").trim();
  if (!name) return "";

  const head = getLegendRiskKey(name);
  return RISK_LABEL_MAP[head] || name;
};

const normalizeLegendColor = (name, color) => {
  const head = getLegendRiskKey(name);
  return RISK_COLOR_MAP[head] || color;
};

class LegendItem extends React.PureComponent {
  static propTypes = {
    size: PropTypes.number,
    color: PropTypes.string,
    name: PropTypes.string,
    icon: PropTypes.string, // triangle, circle, square, line
    hideIcon: PropTypes.bool,
    iconSource: PropTypes.string,
  };

  static defaultProps = {
    size: 12,
    color: "transparent",
    name: "",
    icon: "square",
    hideIcon: false,
    iconSource: "url",
  };

  getIconHtml = (iconName, iconColor) => {
    const { name, hideIcon, color, size, icon, iconSource } = this.props;
    const resolvedColor = iconColor || color;

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
            borderBottomColor: resolvedColor,
          }}
        />
      );
    }

    if (iconName === "line") {
      return (
        <div
          className={`icon-${icon}`}
          style={{ width: size, backgroundColor: resolvedColor }}
        />
      );
    }

    if (iconName === "square" || iconName === "circle") {
      return (
        <div
          className={`icon-${icon}`}
          style={{ width: size, height: size, backgroundColor: resolvedColor }}
        />
      );
    }

    if (iconSource === "sprite") {
      const style = {};

      if (resolvedColor) {
        style.fill = resolvedColor;
      }

      return (
        <div className="custom-icon">
          <Icon icon={`icon-${icon}`} style={{ ...style }} />
        </div>
      );
    }

    return (
      <div className="custom-icon">
        <img src={icon} alt={name} />
      </div>
    );
  };

  render() {
    const { name, icon, color } = this.props;
    const displayName = normalizeLegendName(name);
    const displayColor = normalizeLegendColor(name, color);

    return (
      <div className="c-legend-item-basic">
        {this.getIconHtml(icon || "square", displayColor)}

        <span className="name">{displayName}</span>
      </div>
    );
  }
}

export default LegendItem;
