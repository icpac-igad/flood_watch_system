import React, { PureComponent } from 'react';
import PropTypes from 'prop-types';

import Dropdown from '@/components/ui/dropdown';
import { FilterPanelContainer, WHCAFilterContainer } from '@/services/filters';

import './styles.scss';

// =============================================================================
// FloodWatch Custom: Filter Section with WHCA Countries option
// WHCA = Uganda, Rwanda, South Sudan, Ethiopia, Sudan (5 countries)
// =============================================================================
class FilterSection extends PureComponent {
  static propTypes = {
    selectedFilterType: PropTypes.string,
    setSelectedFilterType: PropTypes.func,
  };

  render() {
    const { selectedFilterType, setSelectedFilterType } = this.props;

    const filterTypeOptions = [
      { label: 'Filter by admin', value: 'admin' },
      { label: 'WHCA Countries', value: 'whca' },  // FloodWatch Custom
      { label: 'Filter by cluster', value: 'cluster' },
      { label: 'Filter by watershed', value: 'watershed' },
      { label: 'Filter by protected areas', value: 'protected' },
    ];

    const selectedOption = filterTypeOptions.find(
      (option) => option.value === selectedFilterType
    );

    return (
      <div className="c-filter-section">
        <div className="filter-type-selector">
          <div className="filter-label">Filter Type</div>
          <Dropdown
            className="filter-type-dropdown"
            theme="theme-dropdown-native"
            options={filterTypeOptions}
            value={selectedOption}
            onChange={(value) => setSelectedFilterType(value)}
            native
          />
        </div>

        {selectedFilterType === 'admin' && (
          <div className="filter-content">
            <FilterPanelContainer />
          </div>
        )}

        {/* FloodWatch Custom: WHCA Countries Filter */}
        {selectedFilterType === 'whca' && (
          <div className="filter-content">
            <WHCAFilterContainer />
          </div>
        )}

        {selectedFilterType !== 'admin' && selectedFilterType !== 'whca' && (
          <div className="filter-placeholder">
            <p>Coming soon...</p>
          </div>
        )}
      </div>
    );
  }
}

export default FilterSection;
