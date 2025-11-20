/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_MAPSERVER_URL?: string;
  readonly VITE_MAPCACHE_WMS_URL?: string;
  readonly VITE_MAPCACHE_TMS_URL?: string;
  readonly VITE_MAPSERVER_DOMAIN?: string;
  readonly VITE_MAPCACHE_DOMAIN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
