import { createSelector, createStructuredSelector } from 'reselect';

const selectUtilityPanel = (state) => state.utilityPanel || {};

export const selectActiveTab = createSelector(
  [selectUtilityPanel],
  (utilityPanel) => utilityPanel.activeTab || 'filter'
);

export const selectSelectedFilterType = createSelector(
  [selectUtilityPanel],
  (utilityPanel) => utilityPanel.selectedFilterType || 'admin'
);

export const selectHidden = createSelector(
  [selectUtilityPanel],
  (utilityPanel) => utilityPanel.hidden || false
);

export const selectCollapsed = createSelector(
  [selectUtilityPanel],
  (utilityPanel) => utilityPanel.collapsed || false
);

export const getUtilityPanelProps = createStructuredSelector({
  activeTab: selectActiveTab,
  selectedFilterType: selectSelectedFilterType,
  hidden: selectHidden,
  collapsed: selectCollapsed,
});
