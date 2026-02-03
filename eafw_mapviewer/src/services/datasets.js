import request from "@/utils/request";

import { CMS_API } from "@/utils/constants";

export const getApiDatasets = () =>
  request.get(`${CMS_API}/datasets`).then((res) => res?.data);
