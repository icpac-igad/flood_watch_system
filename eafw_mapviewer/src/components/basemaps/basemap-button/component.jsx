import cx from "classnames";
import PropTypes from "prop-types";
import defaultBasemapThumb from "@/components/map/images/default.png";

import "./styles.scss";

export const BasemapButton = (props) => {
  const { image, label, active, onSelectBasemap } = props;
  const fallbackImage = image || defaultBasemapThumb || "/favicon/logo.png";

  return (
    <button className="c-basemap-button" onClick={() => onSelectBasemap(props)}>
      <img
        src={fallbackImage}
        alt={label}
        className={cx("basemap-thumb", { "-active": active })}
        onError={(e) => {
          if (e.currentTarget.src.includes("/favicon/logo.png")) return;
          e.currentTarget.src = "/favicon/logo.png";
        }}
      />
      <span>{label}</span>
    </button>
  );
};

BasemapButton.propTypes = {
  image: PropTypes.string,
  label: PropTypes.string,
  active: PropTypes.bool,
  onSelectBasemap: PropTypes.func,
};

export default BasemapButton;
