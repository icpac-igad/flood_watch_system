import React, { PureComponent, Fragment } from "react";
import PropTypes from "prop-types";
import isEmpty from "lodash/isEmpty";
import cx from "classnames";

import NoContent from "@/components/ui/no-content";
import LayerToggle from "@/components/map/components/legend/components/layer-toggle";

import Basemaps from "@/components/basemaps";

import DatasetSection from "./dataset-section";
import CategoriesMenu from "./categories-menu";
import LoginForm from "@/components/forms/login";

import "./styles.scss";

class Datasets extends PureComponent {
  renderLoginWindow() {
    return (
      <div className="login-header">
        <h3 className="title-login">Please log in</h3>
        <p>Log in is required so you can view datasets in this section</p>
        <LoginForm className="my-account-login" simple narrow />
      </div>
    );
  }
  render() {
    const {
      isDesktop,
      datasetCategory,
      datasetCategories,
      menuSection,
      datasets,
      subCategories,
      onToggleLayer,
      setModalMetaSettings,
      setMenuSettings,
      onToggleSubCategoryCollapse,
      onToggleGroupOption,
      id: sectionId,
      subCategoryGroupsSelected,
      loggedIn,
      showBoundaryLayersAtBottom,
    } = this.props;

    const activeDatasetCategory =
      datasetCategory &&
      datasetCategories.find((c) => c.category === datasetCategory);

    const { loginRequired } = activeDatasetCategory || {};

    // Filter out Boundary Layers for counting
    const nonBoundaryCategories = datasetCategories
      ? datasetCategories.filter((c) => c.category !== 'Boundary Layers')
      : [];

    // Show CategoriesMenu only when there are 3+ non-boundary categories
    const shouldShowCategoriesMenu =
      nonBoundaryCategories && nonBoundaryCategories.length > 2;

    // Get Boundary Layers category data
    const boundaryLayersCategory = datasetCategories
      ? datasetCategories.find((c) => c.category === 'Boundary Layers')
      : null;

    return (
      <div className="c-datasets">
        {!isDesktop &&
          menuSection &&
          !datasetCategory &&
          shouldShowCategoriesMenu && (
            <div>
              <Basemaps />
              <CategoriesMenu
                categories={datasetCategories}
                onSelectCategory={setMenuSettings}
              />
            </div>
          )}

        {loginRequired && !loggedIn ? (
          this.renderLoginWindow()
        ) : (
          <>
            {menuSection && datasetCategory && (
              <Fragment>
                {subCategories
                  ? subCategories.map((subCat) => {
                      const groupKey = `${sectionId}-${subCat.id}`;
                      let selectedGroup = subCategoryGroupsSelected[groupKey];
                      // set default group
                      if (
                        !selectedGroup &&
                        subCat.group_options &&
                        !!subCat.group_options.length
                      ) {
                        const defaultGroup =
                          subCat.group_options.find((o) => o.default) ||
                          subCat.group_options[0];

                        selectedGroup = defaultGroup.value;
                      }

                      return (
                        <DatasetSection
                          key={subCat.slug}
                          sectionId={sectionId}
                          {...subCat}
                          onToggleCollapse={onToggleSubCategoryCollapse}
                        >
                          {subCat.group_options && (
                            <div className="group-options-wrapper">
                              {subCat.group_options_title && (
                                <div className="group-options-title">
                                  {subCat.group_options_title}
                                </div>
                              )}
                              <div className="group-options">
                                {subCat.group_options.map((groupOption) => {
                                  return (
                                    <div
                                      key={groupOption.value}
                                      className={cx("group-option", {
                                        active:
                                          groupOption.value === selectedGroup,
                                      })}
                                      onClick={() => {
                                        onToggleGroupOption(
                                          groupKey,
                                          groupOption.value
                                        );
                                      }}
                                    >
                                      {groupOption.label}
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          )}
                          {!isEmpty(subCat.datasets) ? (
                            subCat.datasets.map((d) => {
                              if (
                                d.group &&
                                subCat.group_options &&
                                !!subCat.group_options.length
                              ) {
                                if (d.group && d.group === selectedGroup) {
                                  return (
                                    <LayerToggle
                                      key={d.id}
                                      className="dataset-toggle"
                                      data={{ ...d, dataset: d.id }}
                                      onToggle={onToggleLayer}
                                      onInfoClick={setModalMetaSettings}
                                      category={datasetCategory}
                                    />
                                  );
                                } else {
                                  return null;
                                }
                              }

                              return (
                                <LayerToggle
                                  key={d.id}
                                  className="dataset-toggle"
                                  data={{ ...d, dataset: d.id }}
                                  onToggle={onToggleLayer}
                                  onInfoClick={setModalMetaSettings}
                                  category={datasetCategory}
                                />
                              );
                            })
                          ) : (
                            <NoContent
                              className="no-datasets"
                              message="No datasets available"
                            />
                          )}
                        </DatasetSection>
                      );
                    })
                  : datasets &&
                    datasets.map((d, i) => (
                      <LayerToggle
                        key={d.id}
                        tabIndex={i}
                        className="dataset-toggle"
                        data={{ ...d, dataset: d.id }}
                        onToggle={onToggleLayer}
                        onInfoClick={setModalMetaSettings}
                        category={datasetCategory}
                      />
                    ))}
                {/* Show boundary-layers datasets at bottom only in tab mode (1-2 categories) */}
                {showBoundaryLayersAtBottom && boundaryLayersCategory && datasetCategory !== 'Boundary Layers' && (
                  <div className="boundary-layers-section">
                    <div className="boundary-layers-separator"></div>
                    <h3 className="boundary-layers-heading">Boundary Layers</h3>
                    {boundaryLayersCategory.subCategories
                      ? boundaryLayersCategory.subCategories.map((subCat) => {
                          const groupKey = `${boundaryLayersCategory.id}-${subCat.id}`;
                          let selectedGroup = subCategoryGroupsSelected[groupKey];

                          if (
                            !selectedGroup &&
                            subCat.group_options &&
                            !!subCat.group_options.length
                          ) {
                            const defaultGroup =
                              subCat.group_options.find((o) => o.default) ||
                              subCat.group_options[0];
                            selectedGroup = defaultGroup.value;
                          }

                          return (
                            <DatasetSection
                              key={subCat.slug}
                              sectionId={boundaryLayersCategory.id}
                              {...subCat}
                              onToggleCollapse={onToggleSubCategoryCollapse}
                            >
                              {subCat.group_options && (
                                <div className="group-options-wrapper">
                                  {subCat.group_options_title && (
                                    <div className="group-options-title">
                                      {subCat.group_options_title}
                                    </div>
                                  )}
                                  <div className="group-options">
                                    {subCat.group_options.map((groupOption) => {
                                      return (
                                        <div
                                          key={groupOption.value}
                                          className={cx("group-option", {
                                            active: groupOption.value === selectedGroup,
                                          })}
                                          onClick={() => {
                                            onToggleGroupOption(
                                              groupKey,
                                              groupOption.value
                                            );
                                          }}
                                        >
                                          {groupOption.label}
                                        </div>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}
                              {!isEmpty(subCat.datasets) ? (
                                subCat.datasets.map((d) => {
                                  if (
                                    d.group &&
                                    subCat.group_options &&
                                    !!subCat.group_options.length
                                  ) {
                                    if (d.group && d.group === selectedGroup) {
                                      return (
                                        <LayerToggle
                                          key={d.id}
                                          className="dataset-toggle"
                                          data={{ ...d, dataset: d.id }}
                                          onToggle={onToggleLayer}
                                          onInfoClick={setModalMetaSettings}
                                          category="Boundary Layers"
                                        />
                                      );
                                    } else {
                                      return null;
                                    }
                                  }

                                  return (
                                    <LayerToggle
                                      key={d.id}
                                      className="dataset-toggle"
                                      data={{ ...d, dataset: d.id }}
                                      onToggle={onToggleLayer}
                                      onInfoClick={setModalMetaSettings}
                                      category="Boundary Layers"
                                    />
                                  );
                                })
                              ) : (
                                <NoContent
                                  className="no-datasets"
                                  message="No datasets available"
                                />
                              )}
                            </DatasetSection>
                          );
                        })
                      : boundaryLayersCategory.datasets &&
                        boundaryLayersCategory.datasets.map((d, i) => (
                          <LayerToggle
                            key={d.id}
                            tabIndex={i}
                            className="dataset-toggle"
                            data={{ ...d, dataset: d.id }}
                            onToggle={onToggleLayer}
                            onInfoClick={setModalMetaSettings}
                            category="Boundary Layers"
                          />
                        ))}
                  </div>
                )}
              </Fragment>
            )}
          </>
        )}
      </div>
    );
  }
}

Datasets.propTypes = {
  name: PropTypes.string,
  datasets: PropTypes.array,
  onToggleLayer: PropTypes.func,
  setModalMetaSettings: PropTypes.func,
  subCategories: PropTypes.array,
  selectedCountries: PropTypes.array,
  countries: PropTypes.array,
  setMenuSettings: PropTypes.func,
  countriesWithoutData: PropTypes.array,
  setMapSettings: PropTypes.func,
  activeDatasets: PropTypes.array,
  categories: PropTypes.array,
  category: PropTypes.string,
  section: PropTypes.string,
  isDesktop: PropTypes.bool,
  handleRemoveCountry: PropTypes.func,
  handleAddCountry: PropTypes.func,
  datasetCategory: PropTypes.string,
  datasetCategories: PropTypes.array,
  menuSection: PropTypes.string,
  showBoundaryLayersAtBottom: PropTypes.bool,
};

export default Datasets;
