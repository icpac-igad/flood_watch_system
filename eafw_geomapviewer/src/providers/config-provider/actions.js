import { createAction, createThunkAction } from "@/redux/actions";
import { getConfig } from "@/services/config";
import { CMS_API } from "@/utils/constants";
import {
  setParamInteractions,
  setInitialParamInteractions,
  setInitialBbox,
  setMapSettings,
} from "@/components/map/actions";
import { buildParamInteractionsFromBoundary } from "@/utils/params";
import { fetchGenericBoundaries } from "@/utils/boundary-utils";

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
        boundaryTileParams,
        scopeKey,
        scopeTitle,
        vectorLayerIcons,
        links,
        disclaimerText,
        enableMyAccount,
        allowSignups,
        filterTypes,
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

      const appConfig = {
        logo,
        countries,
        boundaryDataSource,
        boundaryTileParams: boundaryTileParams || "",
        scopeKey: scopeKey || "",
        scopeTitle: scopeTitle || "",
        vectorLayerIcons,
        bounds,
        links,
        disclaimerText,
        enableMyAccount,
        allowSignups,
        filterTypes: filterTypes || [],
        sections: sections,
        basemaps: basemaps.reduce((all, item) => {
          item.value = item.label;
          // Resolve relative image URLs against the CMS base URL
          if (item.image && item.image.startsWith("/")) {
            const cmsBase = CMS_API.replace(/\/api\/?$/, "");
            item.image = `${cmsBase}${item.image}`;
          }
          all[item.label] = item;
          return all;
        }, {}),
      };

      // Auto-apply project scope BEFORE config (so layers load with scope already set)
      if (scopeKey) {
        const SCOPE_COUNTRIES = {
          whca: 'SD,SS,UG,ET,RW',
        };
        dispatch(setParamInteractions({
          scope: scopeKey,
          project_countries: SCOPE_COUNTRIES[scopeKey] || '',
        }));
        if (bounds?.length) {
          dispatch(setInitialBbox(bounds));
        }
      }

      dispatch(setConfig(appConfig));

      // Auto-select the default basemap on load
      const defaultBasemap = basemaps.find((b) => b.default);
      if (defaultBasemap) {
        dispatch(setMapSettings({ basemap: { value: defaultBasemap.label } }));
      }

      // Initialize fixed_code boundary params and bbox on page load.
      // This runs before the filter panel mounts so the map is pre-clipped on load.
      for (const filterType of filterTypes || []) {
        const { levels, boundary_api_url, fixed_project_name, default_code_field, default_name_field } = filterType;

        // Collect consecutive fixed levels from the start
        const fixedLevels = [];
        for (const level of levels) {
          if (level.fixed_code) {
            fixedLevels.push(level);
          } else {
            break;
          }
        }
        if (fixedLevels.length === 0) continue;

        const deepestIndex = fixedLevels.length - 1;
        const deepestLevel = fixedLevels[deepestIndex];
        const rootCode = fixedLevels[0].fixed_code;
        const projectName = fixed_project_name || rootCode;

        const params = buildParamInteractionsFromBoundary(
          { code: deepestLevel.fixed_code },
          deepestLevel.admin_level,
          deepestLevel.border_level || '0',
          projectName
        );

        dispatch(setParamInteractions(params));
        dispatch(setInitialParamInteractions(params));

        // Fetch the fixed boundary's bbox and store as initialBbox so
        // the map component applies it once the map finishes loading.
        const parentCode = deepestIndex === 0 ? '' : fixedLevels[deepestIndex - 1].fixed_code;
        const ancestorMap = {};
        fixedLevels.slice(0, deepestIndex).forEach((level) => {
          if (level.variable_name) ancestorMap[level.variable_name] = level.fixed_code;
        });

        fetchGenericBoundaries(
          boundary_api_url,
          {
            ...deepestLevel,
            code_field: deepestLevel.code_field || default_code_field || 'code',
            name_field: deepestLevel.name_field || default_name_field || 'name',
            include_bbox: true,
          },
          parentCode,
          { ancestorMap }
        ).then((data) => {
          const match = data.find((b) => b.code === deepestLevel.fixed_code);
          if (match?.bbox) {
            const { left, bottom, right, top } = match.bbox;
            dispatch(setInitialBbox([left, bottom, right, top]));
          }
        });

        break; // Only process the first filter type that has fixed levels
      }

      return appConfig;
    } catch (err) {
      dispatch(setConfigLoading({ loading: false, error: true }));
    }
  }
);
