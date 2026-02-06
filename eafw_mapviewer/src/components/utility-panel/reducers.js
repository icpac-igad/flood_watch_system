export const initialState = {
  activeTab: 'filter', // 'filter' | 'draw'
  selectedFilterType: 'project', // 'project' | 'cluster' | 'watershed' | 'protected'
  hidden: false,
  collapsed: false,
};

const setUtilityPanelSettings = (state, { payload }) => ({
  ...state,
  ...payload,
});

const setUtilityActiveTab = (state, { payload }) => ({
  ...state,
  activeTab: payload,
});

const setSelectedFilterType = (state, { payload }) => ({
  ...state,
  selectedFilterType: payload,
});

const reducers = {
  setUtilityPanelSettings,
  setUtilityActiveTab,
  setSelectedFilterType,
};

export default reducers;
