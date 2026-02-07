import React, { PureComponent } from 'react';
import PropTypes from 'prop-types';

import Dropdown from '@/components/ui/dropdown';
import { ProjectFilterContainer, WatershedFilterContainer } from '@/services/filters';

import './styles.scss';

class FilterSection extends PureComponent {
  static propTypes = {
    selectedFilterType: PropTypes.string,
    setSelectedFilterType: PropTypes.func,
    setParamInteractions: PropTypes.func,
  };

  render() {
    const { selectedFilterType, setSelectedFilterType, setParamInteractions } = this.props;

    const filterTypeOptions = [
      { label: 'Filter by project', value: 'project' },
      { label: 'Filter by cluster', value: 'cluster' },
      { label: 'Filter by watershed', value: 'watershed' },
      { label: 'Filter by protected areas', value: 'protected' },
    ];

    const selectedOption = filterTypeOptions.find(
      (option) => option.value === selectedFilterType
    );

    const handleFilterTypeChange = (value) => {
      setSelectedFilterType(value);
      if (setParamInteractions) {
        const resetParams = {};
        if (value !== 'project') {
          resetParams.project_filter = false;
          resetParams.project_countries = '';
        }
        if (value !== 'watershed') {
          resetParams.basin_filter = false;
          resetParams.basin_id = '';
        }
        if (Object.keys(resetParams).length > 0) {
          setParamInteractions(resetParams);
        }
      }
    };

    return (
      <div className="c-filter-section">
        <div className="filter-type-selector">
          <div className="filter-label">Filter Type</div>
          <Dropdown
            className="filter-type-dropdown"
            theme="theme-dropdown-native"
            options={filterTypeOptions}
            value={selectedOption}
            onChange={handleFilterTypeChange}
            native
          />
        </div>

        {selectedFilterType === 'project' && (
          <div className="filter-content">
            <ProjectFilterContainer />
          </div>
        )}

        {selectedFilterType === 'watershed' && (
          <div className="filter-content">
            <WatershedFilterContainer />
          </div>
        )}

        {selectedFilterType !== 'project' && selectedFilterType !== 'watershed' && (
          <div className="filter-placeholder">
            <p>Coming soon...</p>
          </div>
        )}
      </div>
    );
  }
}

export default FilterSection;
