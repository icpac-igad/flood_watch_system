import React from 'react';

import Dropdown from '@/components/ui/dropdown';
import { GenericFilterPanelContainer, ProjectFilterPanelContainer } from '@/services/filters';

import './styles.scss';

const FilterSection = ({ selectedFilterType, setSelectedFilterType, filterTypes }) => {
  const filterTypeOptions = [
    { label: 'Filter by project', value: 'project' },
    ...(filterTypes?.length > 0
      ? filterTypes.map((ft) => ({ label: ft.label, value: ft.value }))
      : []),
  ];

  const selectedOption =
    filterTypeOptions.find((o) => o.value === selectedFilterType) ||
    filterTypeOptions[0];

  const selectedFilterConfig = filterTypes?.find(
    (ft) => ft.value === selectedOption.value
  );
  const isProjectFilter = selectedOption.value === 'project';

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

      {isProjectFilter ? (
        <div className="filter-content">
          <ProjectFilterPanelContainer />
        </div>
      ) : selectedFilterConfig ? (
        <div className="filter-content">
          <GenericFilterPanelContainer filterTypeConfig={selectedFilterConfig} />
        </div>
      ) : (
        <div className="filter-placeholder">
          <p>Coming soon...</p>
        </div>
      )}
    </div>
  );
};

export default FilterSection;
