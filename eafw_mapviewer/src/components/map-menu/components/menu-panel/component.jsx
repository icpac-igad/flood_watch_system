import React, { PureComponent } from "react";
import PropTypes from "prop-types";
import cx from "classnames";
import startCase from "lodash/startCase";

import Loader from "@/components/ui/loader";
import Button from "@/components/ui/button";
import Icon from "@/components/ui/icon";
import closeIcon from "@/assets/icons/close.svg?sprite";
import arrowIcon from "@/assets/icons/arrow-down.svg?sprite";
import posed, { PoseGroup } from "react-pose";
import CategoryTabs from "../category-tabs/component";

import "./styles.scss";

const PanelMobile = posed.div({
  enter: {
    y: 0,
    opacity: 1,
    delay: 200,
    transition: { duration: 200 },
  },
  exit: {
    y: 50,
    opacity: 0,
    delay: 200,
    transition: { duration: 200 },
  },
});

const PanelDesktop = posed.div({
  enter: {
    opacity: 1,
    delay: 300,
  },
  exit: {
    opacity: 0,
    transition: { duration: 200 },
  },
});

class MenuPanel extends PureComponent {
  panelLabel() {
    const { label, category, setMenuSettings } = this.props;
    const isSearch = label.toLowerCase() === "search";

    if (category || isSearch) {
      return (
        <button
          onClick={() =>
            setMenuSettings({
              ...(category && { datasetCategory: "" }),
              ...(isSearch && { searchType: "" }),
            })
          }
        >
          <Icon icon={arrowIcon} className="icon-return" />
          <span>{isSearch ? label : startCase(category)}</span>
        </button>
      );
    }

    return <span>{label}</span>;
  }

  render() {
    const {
      active,
      className,
      isDesktop,
      large,
      onClose,
      onOpen,
      children,
      loading,
      collapsed,
      datasetCategories,
      datasetCategory,
      setMenuSettings,
      searchSections,
      menuSection,
      showChevronToggle,
      chevronLeftIcon,
      chevronRightIcon,
      nonBoundarySections,
    } = this.props;
    const Panel = isDesktop ? PanelDesktop : PanelMobile;

    // Filter out Boundary Layers category for counting
    const nonBoundaryCategories = datasetCategories
      ? datasetCategories.filter((c) => c.category !== 'Boundary Layers')
      : [];

    // Get first search section for the search tab
    const searchSection = searchSections && searchSections.length > 0 ? searchSections[0] : null;

    // Show category tabs when there are 1-2 non-boundary categories
    // Show in datasets (LAYERS) section or search section in tab mode, not in other sections like utility, legend, analysis
    const showCategoryTabs =
      nonBoundaryCategories &&
      nonBoundaryCategories.length > 0 &&
      nonBoundaryCategories.length <= 2 &&
      (menuSection === 'datasets' || menuSection === searchSection?.slug);

    return (
      <>
        <PoseGroup>
          {active && (
            <Panel
              key="menu-container"
              className={cx(
                "c-menu-panel",
                "map-tour-menu-panel",
                { large },
                { "with-tabs": showCategoryTabs },
                className
              )}
            >
              {!isDesktop ? (
                <>
                  <div className="panel-header">
                    <div className="panel-label">{this.panelLabel()}</div>
                    <Button
                      className="panel-close"
                      theme="theme-button-clear"
                      onClick={collapsed ? onOpen : onClose}
                    >
                      <Icon
                        icon={arrowIcon}
                        className={cx("icon-close-panel", { collapsed })}
                      />
                    </Button>
                  </div>
                </>
              ) : (
                <>
                  <button className="close-menu" onClick={onClose}>
                    <Icon icon={closeIcon} className="icon-close-panel" />
                  </button>
                </>
              )}
              {showCategoryTabs && (
                <CategoryTabs
                  categories={nonBoundaryCategories}
                  activeCategory={datasetCategory}
                  onCategoryChange={(category) =>
                    setMenuSettings({
                      menuSection: 'datasets',
                      datasetCategory: category
                    })
                  }
                  searchSection={searchSection}
                  activeMenuSection={menuSection}
                  onSearchClick={() =>
                    setMenuSettings({
                      menuSection: searchSection?.slug || 'search',
                      datasetCategory: ''
                    })
                  }
                />
              )}
              {!loading && <div className="panel-body">{children}</div>}
              {loading && <Loader className="map-menu-loader" />}
            </Panel>
          )}
        </PoseGroup>
        {/* Chevron toggle for tab mode - always visible when in tab mode */}
        {showChevronToggle && isDesktop && (
          <button
            className={cx("panel-chevron-toggle", { active })}
            onClick={() => {
              if (active) {
                // Close panel
                setMenuSettings({
                  menuSection: "",
                  datasetCategory: "",
                });
              } else {
                // Open with first category
                const firstCategory = nonBoundarySections && nonBoundarySections[0];
                setMenuSettings({
                  menuSection: "datasets",
                  datasetCategory: firstCategory?.category || "",
                });
              }
            }}
          >
            <Icon
              icon={active ? chevronLeftIcon : chevronRightIcon}
              className="panel-chevron-icon"
            />
          </button>
        )}
      </>
    );
  }
}

MenuPanel.propTypes = {
  children: PropTypes.node,
  large: PropTypes.bool,
  className: PropTypes.string,
  onClose: PropTypes.func,
  setMenuSettings: PropTypes.func,
  isDesktop: PropTypes.bool,
  label: PropTypes.string,
  category: PropTypes.string,
  active: PropTypes.bool,
  loading: PropTypes.bool,
  collapsed: PropTypes.bool,
  onOpen: PropTypes.func,
  datasetCategories: PropTypes.array,
  datasetCategory: PropTypes.string,
  searchSections: PropTypes.array,
  menuSection: PropTypes.string,
  showChevronToggle: PropTypes.bool,
  chevronLeftIcon: PropTypes.string,
  chevronRightIcon: PropTypes.string,
  nonBoundarySections: PropTypes.array,
};

export default MenuPanel;
