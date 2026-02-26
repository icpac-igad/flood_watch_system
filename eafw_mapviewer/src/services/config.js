import request from "@/utils/request";
import { FASTAPI_API } from "@/utils/constants";

export const getConfig = () =>
  request
    .get(`${FASTAPI_API}/mapviewer-config`, {
      params: { _ts: Date.now() },
      headers: { "Cache-Control": "no-cache" },
    })
    .then((res) => res?.data);
