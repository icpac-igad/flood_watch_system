import { apiRequest } from "@/utils/request";

export const getConfig = () => {
  // Read ?scope= from the browser URL to support project-scoped mapviewer
  const urlParams = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : null;
  const scope = urlParams?.get("scope") || "";
  const url = scope ? `/mapviewer-config?scope=${encodeURIComponent(scope)}` : "/mapviewer-config";
  return apiRequest.get(url).then((res) => res?.data);
};
