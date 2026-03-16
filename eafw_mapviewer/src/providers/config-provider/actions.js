import { createAction, createThunkAction } from "@/redux/actions";
import { getConfig } from "@/services/config";

import defaultThumb from "@/components/map/images/default.png";
import satelliteThumb from "@/components/map/images/satellite.png";
import osmThumb from "@/components/map/images/osm.png";

const BASEMAP_THUMBS = {
  "current basemap": defaultThumb,
  "esri world imagery": satelliteThumb,
  "openstreetmap": osmThumb,
};

export const setConfigLoading = createAction("setConfigLoading");
export const setConfig = createAction("setConfig");
export const setSubCategorySettings = createAction("setSubCategorySettings");

export const fetchConfig = createThunkAction(
  "fetchConfig",
  () => async (dispatch) => {
    dispatch(setConfigLoading({ loading: true, error: false }));

    try {
      const config = await getConfig();
      const {
        categories,
        basemaps,
        countries,
        logo,
        bounds,
        boundaryDataSource,
        vectorLayerIcons,
        links,
        disclaimerText,
        enableMyAccount,
        allowSignups,
        multimodalClusterConfig,
      } = config;

      const sections = categories
        .filter((c) => c.active)
        .map((s) => ({
          label: "layers",
          slug: "datasets",
          category: s.title,
          id: s.id,
          icon: s.icon,
          subCategories: s.sub_categories
            .filter((s_1) => s_1.active)
            .map((subcat) => ({
              ...subcat,
              id: subcat.id,
              title: subcat.title,
              slug: subcat.id,
            })),
        }));

      // Cache-bust mapStyle URLs so the browser always fetches a fresh
      // style JSON (glyphs URL, sources, etc.) on each page load.
      const styleCacheBust = Date.now();

      const appConfig = {
        logo,
        countries,
        boundaryDataSource,
        vectorLayerIcons,
        bounds,
        links,
        disclaimerText,
        enableMyAccount,
        allowSignups,
        multimodalClusterConfig,
        sections: sections,
        basemaps: basemaps.reduce((all, item) => {
          item.value = item.label;
          if (item.mapStyle) {
            const sep = item.mapStyle.includes("?") ? "&" : "?";
            item.mapStyle = `${item.mapStyle}${sep}_ts=${styleCacheBust}`;
          }
          if (!item.image) {
            const key = item.label.toLowerCase();
            item.image = BASEMAP_THUMBS[key] || defaultThumb;
          }
          all[item.label] = item;
          return all;
        }, {}),
      };

      dispatch(setConfig(appConfig));


      return appConfig;
    } catch (err) {
      dispatch(setConfigLoading({ loading: false, error: true }));
    }
  }
);
