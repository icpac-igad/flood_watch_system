import React, { PureComponent } from "react";
import PropTypes from "prop-types";
import cx from "classnames";
import remove from "lodash/remove";
import { trackEvent } from "@/utils/analytics";

import MenuPanel from "./components/menu-panel";
import MenuDesktop from "./components/menu-desktop";
import MenuMobile from "./components/menu-mobile";

import chevronLeftIcon from "@/assets/icons/chevron-left.svg?sprite";
import chevronRightIcon from "@/assets/icons/chevron-right.svg?sprite";

import "./styles.scss";

class MapMenu extends PureComponent {
  getDatasetOrderMap = () => {
    const { datasetSections } = this.props;
    const orderMap = new Map();
    let currentIndex = 0;

    (datasetSections || []).forEach((section) => {
      if (section.subCategories && section.subCategories.length) {
        section.subCategories.forEach((subCategory) => {
          (subCategory.datasets || []).forEach((dataset) => {
            if (!orderMap.has(dataset.id)) {
              orderMap.set(dataset.id, currentIndex++);
            }
          });
        });
        return;
      }

      (section.datasets || []).forEach((dataset) => {
        if (!orderMap.has(dataset.id)) {
          orderMap.set(dataset.id, currentIndex++);
        }
      });
    });

    return orderMap;
  };

  sortActiveDatasetsByCmsOrder = (activeDatasets = []) => {
    const orderMap = this.getDatasetOrderMap();
    const fallback = Number.MAX_SAFE_INTEGER;

    return [...activeDatasets].sort((a, b) => {
      const aIndex = orderMap.has(a.dataset) ? orderMap.get(a.dataset) : fallback;
      const bIndex = orderMap.has(b.dataset) ? orderMap.get(b.dataset) : fallback;
      return aIndex - bIndex;
    });
  };

  reorderActiveDatasetsIfNeeded = () => {
    const { activeDatasets, setMapSettings } = this.props;
    if (!activeDatasets || !activeDatasets.length) return;

    const sorted = this.sortActiveDatasetsByCmsOrder(activeDatasets);
    const changed = sorted.some(
      (dataset, index) => dataset.dataset !== activeDatasets[index]?.dataset
    );

    if (changed) {
      setMapSettings({ datasets: sorted });
    }
  };

  componentDidMount() {
    const { datasetSections } = this.props;
    // If datasets are already loaded at mount, auto-open with delay
    if (datasetSections && datasetSections.length > 0) {
      this.reorderActiveDatasetsIfNeeded();
      setTimeout(() => {
        this.handleAutoOpen();
      }, 150);
    }
  }

  componentDidUpdate(prevProps) {
    const { comparing, activeDatasets, activeCompareSide, setMapSettings, datasetSections } =
      this.props;

    // Handle auto-open when datasetSections loads after mount
    if ((!prevProps.datasetSections || prevProps.datasetSections.length === 0) &&
        datasetSections && datasetSections.length > 0) {
      this.reorderActiveDatasetsIfNeeded();
      // Small delay to ensure URL restoration completes first
      setTimeout(() => {
        this.handleAutoOpen();
      }, 150);
    }
    const { comparing: prevComparing } = prevProps;

    // set all existing layers to a default map side
    if (prevComparing !== comparing) {
      let newActiveDatasets = [...activeDatasets];

      const datasets = newActiveDatasets.map((d) => ({
        ...d,
        mapSide: activeCompareSide,
      }));

      setMapSettings({
        datasets: datasets,
      });
    }
  }

  onToggleLayer = (data, enable) => {
    const { activeDatasets, activeCompareSide } = this.props;
    const { dataset, layer } = data;

    let newActiveDatasets = [...activeDatasets];
    if (!enable) {
      newActiveDatasets = remove(
        newActiveDatasets,
        (l) => l.dataset !== dataset
      );
    } else {
      newActiveDatasets = this.sortActiveDatasetsByCmsOrder([
        ...newActiveDatasets,
        {
          dataset,
          opacity: 1,
          visibility: true,
          layers: [layer],
          ...(activeCompareSide && {
            mapSide: activeCompareSide,
          }),
        },
      ]);
    }

    this.props.setMapSettings({
      datasets: newActiveDatasets || [],
      ...(enable && { canBound: true }),
    });

    trackEvent({
      category: "Map data",
      action: enable ? "User turns on a layer" : "User turns off a layer",
      label: layer,
    });
  };

  // Helper to get non-boundary sections
  getNonBoundarySections = () => {
    const { datasetSections } = this.props;
    return datasetSections
      ? datasetSections.filter((s) => s.category !== 'Boundary Layers')
      : [];
  };

  handleAutoOpen = () => {
    const { menuSection, datasetCategory, setMenuSettings } = this.props;

    const nonBoundarySections = this.getNonBoundarySections();

    // Auto-open with first non-boundary category when there are 1-2 non-boundary categories
    // Check both menuSection and datasetCategory to ensure we're in initial state
    if (
      nonBoundarySections &&
      nonBoundarySections.length > 0 &&
      nonBoundarySections.length <= 2 &&
      (menuSection === undefined || menuSection === null || menuSection === "") &&
      (datasetCategory === undefined || datasetCategory === null || datasetCategory === "")
    ) {
      const firstCategory = nonBoundarySections[0];
      setMenuSettings({
        menuSection: "datasets",
        datasetCategory: firstCategory.category,
      });
    }
  };

  onToggleMobileMenu = (slug) => {
    const { setMenuSettings } = this.props;

    if (slug) {
      setMenuSettings({ menuSection: slug });
      trackEvent({
        category: "Map menu",
        action: "Select Map menu",
        label: slug,
      });
    } else {
      setMenuSettings({
        menuSection: "",
      });
    }
  };

  render() {
    const {
      className,
      upperSections,
      datasetSections,
      searchSections,
      mobileSections,
      activeSection,
      setMenuSettings,
      setSubCategorySettings,
      menuSection,
      loading,
      analysisLoading,
      embed,
      isDesktop,
      recentActive,
      subCategoryGroupsSelected,
      ...props
    } = this.props;
    const {
      Component,
      label,
      category,
      large,
      icon,
      collapsed,
      openSection,
      ...rest
    } = activeSection || {};

    const nonBoundarySections = this.getNonBoundarySections();

    // Show category panel only when there are 3+ non-boundary categories
    const showCategoryPanel = !nonBoundarySections || nonBoundarySections.length > 2;

    return (
      <div className={cx("c-map-menu", className)}>
        {/* Only show menu-tiles on mobile or when showing tile-based navigation (3+ categories) */}
        {(!isDesktop || (isDesktop && !embed && showCategoryPanel)) && (
          <div className={cx("menu-tiles", "map-tour-data-layers", { embed })}>
            {isDesktop && !embed && showCategoryPanel && (
              <MenuDesktop
                className="menu-desktop"
                datasetSections={datasetSections}
                searchSections={searchSections}
                setMenuSettings={setMenuSettings}
                upperSections={upperSections}
              />
            )}
            {!isDesktop && (
              <MenuMobile
                sections={mobileSections}
                onToggleMenu={this.onToggleMobileMenu}
              />
            )}
          </div>
        )}
        <MenuPanel
          className={cx("menu-panel", menuSection)}
          label={label}
          category={category}
          active={!!menuSection}
          large={large}
          isDesktop={isDesktop}
          setMenuSettings={setMenuSettings}
          loading={loading}
          collapsed={collapsed}
          datasetCategories={this.props.datasetCategories}
          datasetCategory={this.props.datasetCategory}
          searchSections={searchSections}
          menuSection={menuSection}
          showChevronToggle={!showCategoryPanel}
          chevronLeftIcon={chevronLeftIcon}
          chevronRightIcon={chevronRightIcon}
          nonBoundarySections={nonBoundarySections}
          onClose={() =>
            setMenuSettings({
              menuSection: "",
              datasetCategory: "",
            })
          }
          onOpen={() => setMenuSettings({ menuSection: openSection })}
        >
          {Component && (
            <Component
              menuSection={menuSection}
              isDesktop={isDesktop}
              setMenuSettings={setMenuSettings}
              onToggleLayer={this.onToggleLayer}
              onToggleSubCategoryCollapse={setSubCategorySettings}
              subCategoryGroupsSelected={subCategoryGroupsSelected}
              showBoundaryLayersAtBottom={!showCategoryPanel}
              onToggleGroupOption={(groupKey, groupOptionValue) => {
                setMenuSettings({
                  subCategoryGroupsSelected: {
                    ...subCategoryGroupsSelected,
                    [groupKey]: groupOptionValue,
                  },
                });
              }}
              {...props}
              {...rest}
            />
          )}
        </MenuPanel>
      </div>
    );
  }
}

MapMenu.propTypes = {
  sections: PropTypes.array,
  className: PropTypes.string,
  datasetSections: PropTypes.array,
  searchSections: PropTypes.array,
  mobileSections: PropTypes.array,
  activeSection: PropTypes.object,
  setMenuSettings: PropTypes.func,
  layers: PropTypes.array,
  zoom: PropTypes.number,
  loading: PropTypes.bool,
  analysisLoading: PropTypes.bool,
  countries: PropTypes.array,
  countriesWithoutData: PropTypes.array,
  activeDatasets: PropTypes.array,
  setMapSettings: PropTypes.func,
  handleClickLocation: PropTypes.func,
  getLocationFromSearch: PropTypes.func,
  exploreSection: PropTypes.string,
  menuSection: PropTypes.string,
  datasetCategory: PropTypes.string,
  showAnalysis: PropTypes.func,
  location: PropTypes.object,
  isDesktop: PropTypes.bool,
  embed: PropTypes.bool,
  setMapPromptsSettings: PropTypes.func,
};

export default MapMenu;
