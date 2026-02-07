import React, { PureComponent } from "react";
import PropTypes from "prop-types";
import cx from "classnames";

import Icon from "@/components/ui/icon";

import "./styles.scss";

class CategoryTabs extends PureComponent {
  render() {
    const {
      categories,
      activeCategory,
      onCategoryChange,
      searchSection,
      activeMenuSection,
      onSearchClick
    } = this.props;

    if (!categories || categories.length === 0) return null;

    const isSearchActive = activeMenuSection === searchSection?.slug;

    return (
      <div className="c-category-tabs">
        {categories.map((category) => (
          <button
            key={category.category}
            className={cx("category-tab", {
              active: activeCategory === category.category && !isSearchActive,
            })}
            onClick={() => onCategoryChange(category.category)}
          >
            {category.icon && <Icon icon={category.icon} className="tab-icon" />}
            <span className="tab-label">{category.label}</span>
          </button>
        ))}
        {searchSection && (
          <button
            key="search"
            className={cx("category-tab", "search-tab", {
              active: isSearchActive,
            })}
            onClick={onSearchClick}
          >
            {searchSection.icon && <Icon icon={searchSection.icon} className="tab-icon" />}
            <span className="tab-label">{searchSection.label}</span>
          </button>
        )}
      </div>
    );
  }
}

CategoryTabs.propTypes = {
  categories: PropTypes.array,
  activeCategory: PropTypes.string,
  onCategoryChange: PropTypes.func,
  searchSection: PropTypes.object,
  activeMenuSection: PropTypes.string,
  onSearchClick: PropTypes.func,
};

export default CategoryTabs;
