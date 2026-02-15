import React, { PureComponent } from "react";
import PropTypes from "prop-types";
import cx from "classnames";
import startCase from "lodash/startCase";
import { trackEvent } from "@/utils/analytics";

import MenuTile from "../menu-tile";

import "./styles.scss";

class MenuDesktop extends PureComponent {
  render() {
    const {
      className,
      upperSections,
      datasetSections,
      searchSections,
      setMenuSettings,
    } = this.props;
    const searchSection =
      searchSections && searchSections.find((s) => s.slug === "search");
    const otherSearchSections = searchSections
      ? searchSections.filter((s) => s.slug !== "search")
      : [];
    const visibleDatasetSections = datasetSections
      ? datasetSections.filter((s) => !s.hiddenMobile)
      : [];

    let orderedMainTiles = [...visibleDatasetSections];
    if (searchSection) {
      const boundaryLayersIndex = orderedMainTiles.findIndex(
        (s) => s.category === "Boundary Layers"
      );
      const searchInsertIndex =
        boundaryLayersIndex >= 0
          ? boundaryLayersIndex + 1
          : orderedMainTiles.length;
      orderedMainTiles.splice(searchInsertIndex, 0, {
        ...searchSection,
        isSearchShortcut: true,
      });
    }

    // Filter out Boundary Layers category for counting
    const nonBoundarySections = datasetSections
      ? datasetSections.filter((s) => s.category !== 'Boundary Layers')
      : [];

    // Hide category tiles when there are 1-2 non-boundary categories (tabs will be shown instead)
    const shouldShowCategoryTiles =
      !nonBoundarySections || nonBoundarySections.length > 2;

    return (
      <div className={cx("c-menu-desktop", className)}>
        <ul className="datasets-menu">
          {upperSections && !!upperSections.length && (
            <div className="upper-sections">
              {upperSections.map((s) => (
                <MenuTile
                  className="search-tile"
                  key={s.slug}
                  onClick={() => {
                    setMenuSettings({
                      menuSection: s.active ? "" : s.slug,
                      datasetCategory: "",
                    });
                    if (!s.active) {
                      trackEvent({
                        category: "Map menu",
                        action: "Select Map menu",
                        label: s.slug,
                      });
                    }
                  }}
                  {...s}
                />
              ))}
            </div>
          )}
          {shouldShowCategoryTiles &&
            orderedMainTiles.map((s) => (
                <MenuTile
                  className={s.isSearchShortcut ? "search-tile" : "datasets-tile"}
                  key={`${s.slug}_${s.category || "search"}`}
                  {...s}
                  label={s.isSearchShortcut ? s.label : s.category}
                  onClick={() => {
                    if (s.isSearchShortcut) {
                      setMenuSettings({
                        menuSection: s.active ? "" : s.slug,
                        datasetCategory: "",
                      });
                    } else {
                      setMenuSettings({
                        datasetCategory: s.active ? "" : s.category,
                        menuSection: s.active ? "" : s.slug,
                      });
                    }
                    if (!s.active) {
                      trackEvent({
                        category: "Map menu",
                        action: "Select Map menu",
                        label: s.slug,
                      });
                    }
                  }}
                />
              ))}
        </ul>
        {!!otherSearchSections.length && (
          <ul className="datasets-menu">
            {otherSearchSections.map((s) => (
              <MenuTile
                className="search-tile"
                key={s.slug}
                onClick={() => {
                  setMenuSettings({
                    menuSection: s.active ? "" : s.slug,
                    datasetCategory: "",
                  });
                  if (!s.active) {
                    trackEvent({
                      category: "Map menu",
                      action: "Select Map menu",
                      label: s.slug,
                    });
                  }
                }}
                {...s}
              />
            ))}
          </ul>
        )}
      </div>
    );
  }
}

MenuDesktop.propTypes = {
  upperSections: PropTypes.array,
  datasetSections: PropTypes.array,
  searchSections: PropTypes.array,
  setMenuSettings: PropTypes.func,
  className: PropTypes.string,
};

export default MenuDesktop;
