import request from "@/utils/request";
import { FASTAPI_API } from "@/utils/constants";

export const getConfig = () =>
  request.get(`${FASTAPI_API}/mapviewer-config`).then((res) => res?.data);
