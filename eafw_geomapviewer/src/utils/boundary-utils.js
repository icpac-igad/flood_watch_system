import { boundaryApiRequest } from "@/utils/request";

export const fetchGenericBoundaries = async (
  apiUrl,
  levelConfig,
  parentCode,
  { boundaryData, setBoundaryData, ancestorMap = {} } = {}
) => {
  // Resolve {variable_name} placeholders in extra_api_params.
  // e.g. {cluster} is replaced with the code selected at the level whose variable_name is "cluster".
  const resolvedExtraParams = (levelConfig.extra_api_params || '').replace(
    /\{([^}]+)\}/g,
    (_, name) => ancestorMap[name] || ''
  );

  // Include resolved params in cache key so different ancestor combos don't collide.
  const cacheKey = `generic_${apiUrl}_${levelConfig.admin_level}_${parentCode || 'root'}_${resolvedExtraParams}`;
  if (boundaryData?.[cacheKey]) return boundaryData[cacheKey];

  try {
    const params = {};
    if (resolvedExtraParams) {
      new URLSearchParams(resolvedExtraParams).forEach((v, k) => {
        params[k] = v;
      });
    }
    if (levelConfig.include_bbox) {
      params.with_bbox = 'true';
    }
    if (levelConfig.parent_param && parentCode) {
      params[levelConfig.parent_param] = parentCode;
    }

    const response = await boundaryApiRequest.get(apiUrl, { params });

    const data = (response.data || []).map((item) => ({
      code: item[levelConfig.code_field],
      name: item[levelConfig.name_field],
      bbox: item.bbox || null,
    }));

    if (setBoundaryData) setBoundaryData({ key: cacheKey, data });
    return data;
  } catch (error) {
    console.error('Error fetching boundaries:', error);
    return [];
  }
};
