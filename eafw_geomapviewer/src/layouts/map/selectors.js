import { createSelector, createStructuredSelector } from "reselect";

import {
  getActiveDatasetsFromState,
  getBasemapFromState,
} from "@/components/map/selectors";

import { getNonBoundaryCategories } from "@/components/map-menu/selectors";

const getMainMapSettings = (state) => state.mainMap || {};
const selectLocation = (state) => state.location && state.location;
const selectLocationPayload = (state) =>
  state.location && state.location.payload;
const selectMenuSection = (state) => state.mapMenu?.settings?.menuSection;
const getDrawGeostoreId = (state) => state.draw && state.draw.geostoreId;
const selectMapPrinting = (state) => state.map && state.map?.settings?.printing;

const getActiveSection = createSelector(
  [selectMenuSection],
  (menuSection) => {
    if (menuSection === 'search') {
      return { large: true };
    }
    return { large: false };
  }
);

// SELECTORS
export const getEmbed = createSelector([selectLocation], (location) => {
  return location && location?.pathname?.includes("/embed");
});

export const getHidePanels = createSelector(
  getMainMapSettings,
  (settings) => settings.hidePanels
);

export const getShowBasemaps = createSelector(
  getMainMapSettings,
  (settings) => settings.showBasemaps
);

export const getShowRecentImagery = createSelector(
  getMainMapSettings,
  (settings) => settings.showRecentImagery
);

export const getHideLegend = createSelector(
  getMainMapSettings,
  (settings) => settings.hideLegend
);

export const getShowAnalysis = createSelector(
  getMainMapSettings,
  (settings) => settings.showAnalysis
);

// Determine if we should show category panel (tile mode) or use tabs
export const getShowCategoryPanel = createSelector(
  [getNonBoundaryCategories],
  (nonBoundaryCategories) =>
    !nonBoundaryCategories || nonBoundaryCategories.length > 2
);

export const getMapProps = createStructuredSelector({
  analysisActive: getShowAnalysis,
  recentActive: getShowRecentImagery,
  hidePanels: getHidePanels,
  menuSection: selectMenuSection,
  activeSection: getActiveSection,
  activeDatasets: getActiveDatasetsFromState,
  embed: getEmbed,
  geostoreId: getDrawGeostoreId,
  location: selectLocationPayload,
  basemap: getBasemapFromState,
  mapPrinting: selectMapPrinting,
  showCategoryPanel: getShowCategoryPanel,
});
