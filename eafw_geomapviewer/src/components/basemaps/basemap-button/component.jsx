import cx from "classnames";
import PropTypes from "prop-types";
import defaultBasemapThumb from "@/components/map/images/default.png";
import darkBasemapThumb from "@/components/map/images/dark.png";
import satelliteBasemapThumb from "@/components/map/images/satellite.png";
import landsatBasemapThumb from "@/components/map/images/landsat.png";
import osmBasemapThumb from "@/components/map/images/osm.png";

import "./styles.scss";

const LOCAL_BASEMAP_IMAGES = {
  default: defaultBasemapThumb,
  dark: darkBasemapThumb,
  satellite: satelliteBasemapThumb,
  landsat: landsatBasemapThumb,
  esri: satelliteBasemapThumb,
  osm: osmBasemapThumb,
};

export const BasemapButton = (props) => {
  const { image, label, active, onSelectBasemap } = props;
  const localImage = LOCAL_BASEMAP_IMAGES[label];
  const fallbackImage = localImage || image || defaultBasemapThumb;

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
