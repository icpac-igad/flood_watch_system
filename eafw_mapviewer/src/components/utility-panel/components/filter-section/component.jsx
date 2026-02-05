import React, { PureComponent } from 'react';
import PropTypes from 'prop-types';

import Dropdown from '@/components/ui/dropdown';
import { FilterPanelContainer, WHCAFilterContainer } from '@/services/filters';

import './styles.scss';

// =============================================================================
// FloodWatch Custom: Filter Section with WHCA Countries option
// WHCA = Uganda, Rwanda, South Sudan, Ethiopia, Sudan (5 countries)
// =============================================================================
const ENABLE_WHCA_FILTER = false;

class FilterSection extends PureComponent {
  static propTypes = {
    selectedFilterType: PropTypes.string,
    setSelectedFilterType: PropTypes.func,
    setParamInteractions: PropTypes.func,
  };

  componentDidMount() {
    const { selectedFilterType, setParamInteractions } = this.props;
    if (selectedFilterType !== 'whca' && setParamInteractions) {
      setParamInteractions({ whca_filter: false, whca_countries: '' });
    }
  }

  componentDidUpdate(prevProps) {
    const { selectedFilterType, setParamInteractions } = this.props;
    if (prevProps.selectedFilterType !== selectedFilterType &&
        selectedFilterType !== 'whca' &&
        setParamInteractions) {
      setParamInteractions({ whca_filter: false, whca_countries: '' });
    }
  }

  render() {
    const { selectedFilterType, setSelectedFilterType, setParamInteractions } = this.props;

    const filterTypeOptions = [
      { label: 'Filter by admin', value: 'admin' },
      ...(ENABLE_WHCA_FILTER ? [{ label: 'WHCA Countries', value: 'whca' }] : []),
      { label: 'Filter by cluster', value: 'cluster' },
      { label: 'Filter by watershed', value: 'watershed' },
      { label: 'Filter by protected areas', value: 'protected' },
    ];

    const selectedOption = filterTypeOptions.find(
      (option) => option.value === selectedFilterType
    );

    const handleFilterTypeChange = (value) => {
      setSelectedFilterType(value);
      if (value !== 'whca' && setParamInteractions) {
        setParamInteractions({ whca_filter: false, whca_countries: '' });
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

        {selectedFilterType === 'admin' && (
          <div className="filter-content">
            <FilterPanelContainer />
          </div>
        )}

        {/* FloodWatch Custom: WHCA Countries Filter */}
        {ENABLE_WHCA_FILTER && selectedFilterType === 'whca' && (
          <div className="filter-content">
            <WHCAFilterContainer />
          </div>
        )}

        {selectedFilterType !== 'admin' && (!ENABLE_WHCA_FILTER || selectedFilterType !== 'whca') && (
          <div className="filter-placeholder">
            <p>Coming soon...</p>
          </div>
        )}
      </div>
    );
  }
}

export default FilterSection;
