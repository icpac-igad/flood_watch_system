#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

COMPOSE_FILE="docker-compose.yml"
ENV_FILE=""
BASE_URL=""

DO_SYNC_MAPFILES=false
DO_CLEAR_MAPCACHE=false
DO_RESTART=false
DO_SMOKE_TEST=false

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

usage() {
  cat <<'USAGE'
Usage: scripts/manage_map_services.sh [options]

Options:
  --compose-file <path>   Compose file to use (default: docker-compose.yml)
  --env-file <path>       Env file for docker compose (default: .env if present)
  --base-url <url>        Public base URL for smoke tests (default resolved from env)

Actions:
  --sync-mapfiles         Sync mapfiles into data/mapfiles
  --clear-mapcache        Clear mapcache tile files (/opt/tiles/*)
  --restart               Restart map stack (mapserver, mapcache, nginx)
  --smoke-test            Run mapserver/mapcache smoke tests via nginx
  --all                   sync-mapfiles + restart + smoke-test
  --all-with-cache        sync-mapfiles + clear-mapcache + restart + smoke-test

Examples:
  scripts/manage_map_services.sh --all
  scripts/manage_map_services.sh --compose-file docker-compose.staging.yml --env-file .env --all-with-cache
  scripts/manage_map_services.sh --smoke-test --base-url http://127.0.0.1:9068
USAGE
}

if [[ -z "${ENV_FILE}" && -f "${REPO_ROOT}/.env" ]]; then
  ENV_FILE="${REPO_ROOT}/.env"
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --compose-file)
      COMPOSE_FILE="$2"
      shift 2
      ;;
    --env-file)
      ENV_FILE="$2"
      shift 2
      ;;
    --base-url)
      BASE_URL="$2"
      shift 2
      ;;
    --sync-mapfiles)
      DO_SYNC_MAPFILES=true
      shift
      ;;
    --clear-mapcache)
      DO_CLEAR_MAPCACHE=true
      shift
      ;;
    --restart)
      DO_RESTART=true
      shift
      ;;
    --smoke-test)
      DO_SMOKE_TEST=true
      shift
      ;;
    --all)
      DO_SYNC_MAPFILES=true
      DO_RESTART=true
      DO_SMOKE_TEST=true
      shift
      ;;
    --all-with-cache)
      DO_SYNC_MAPFILES=true
      DO_CLEAR_MAPCACHE=true
      DO_RESTART=true
      DO_SMOKE_TEST=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ "${DO_SYNC_MAPFILES}" == false && "${DO_CLEAR_MAPCACHE}" == false && "${DO_RESTART}" == false && "${DO_SMOKE_TEST}" == false ]]; then
  # Default action for convenience
  DO_SYNC_MAPFILES=true
  DO_RESTART=true
  DO_SMOKE_TEST=true
fi

COMPOSE_PATH="${COMPOSE_FILE}"
if [[ ! -f "${COMPOSE_PATH}" ]]; then
  COMPOSE_PATH="${REPO_ROOT}/${COMPOSE_FILE}"
fi
if [[ ! -f "${COMPOSE_PATH}" ]]; then
  echo "Compose file not found: ${COMPOSE_FILE}" >&2
  exit 1
fi

compose_cmd() {
  local cmd=(docker compose -f "${COMPOSE_PATH}")
  if [[ -n "${ENV_FILE}" && -f "${ENV_FILE}" ]]; then
    cmd+=(--env-file "${ENV_FILE}")
  fi
  "${cmd[@]}" "$@"
}

resolve_base_url() {
  if [[ -n "${BASE_URL}" ]]; then
    printf '%s' "${BASE_URL}"
    return
  fi

  local host="127.0.0.1"
  local port="9068"

  if [[ -n "${ENV_FILE}" && -f "${ENV_FILE}" ]]; then
    local bind
    bind="$(awk -F= '/^[[:space:]]*NGINX_HOST_BIND=/{gsub(/^[[:space:]]+|[[:space:]]+$/, "", $2); print $2; exit}' "${ENV_FILE}" || true)"
    local env_port
    env_port="$(awk -F= '/^[[:space:]]*NGINX_HOST_PORT=/{gsub(/^[[:space:]]+|[[:space:]]+$/, "", $2); print $2; exit}' "${ENV_FILE}" || true)"

    if [[ -n "${env_port}" ]]; then
      port="${env_port}"
    fi

    if [[ -n "${bind}" && "${bind}" != "0.0.0.0" && "${bind}" != "::" ]]; then
      host="${bind}"
    fi
  fi

  printf 'http://%s:%s' "${host}" "${port}"
}

sync_mapfiles() {
  local src="${REPO_ROOT}/eafw_docker/mapserver/mapfiles"
  local dst="${REPO_ROOT}/data/mapfiles"

  if [[ ! -d "${src}" ]]; then
    echo "Mapfiles source directory missing: ${src}" >&2
    return 1
  fi

  mkdir -p "${dst}"
  log "Syncing mapfiles from ${src} to ${dst}"

  docker run --rm \
    -v "${src}:/src:ro,z" \
    -v "${dst}:/dst:z" \
    alpine:3.20 sh -c 'set -e; rm -rf /dst/*; cp -r /src/. /dst/; chmod -R a+rwX /dst'

  local required=(
    "${dst}/mapserver.conf"
    "${dst}/mapserver.map"
    "${dst}/config/database.map"
    "${dst}/layers/wrf-extreme-rainfall.map"
  )

  for file in "${required[@]}"; do
    if [[ ! -f "${file}" ]]; then
      echo "Required mapfile missing after sync: ${file}" >&2
      return 1
    fi
  done

  log "Mapfiles sync complete"
}

clear_mapcache() {
  log "Clearing mapcache tile files"
  compose_cmd up -d eafw_mapcache >/dev/null
  compose_cmd exec -T eafw_mapcache sh -lc 'rm -rf /opt/tiles/* && mkdir -p /opt/tiles'
  log "Mapcache tile files cleared"
}

restart_map_stack() {
  log "Restarting map stack (mapserver, mapcache, nginx)"
  # Force recreate so mapserver entrypoint re-renders placeholders after mapfile sync.
  compose_cmd up -d --force-recreate eafw_mapserver eafw_mapcache eafw_nginx
}

smoke_test() {
  local url
  url="$(resolve_base_url)"
  log "Running smoke tests via ${url}"

  local mapserver_test="${url}/mapserver/?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&FORMAT=image/png&TRANSPARENT=true&LAYERS=wrf_extreme_very_heavy&STYLES=&WIDTH=64&HEIGHT=64&SRS=EPSG:3857&BBOX=0,0,20037508.342789244,20037508.342789244"
  local mapcache_test="${url}/mapcache/"

  local mapserver_headers="/tmp/eafw-mapserver-smoke.headers"
  local mapserver_body="/tmp/eafw-mapserver-smoke.png"
  local mapserver_ok=false
  for _ in $(seq 1 6); do
    if curl -fsS --max-time 20 -D "${mapserver_headers}" "${mapserver_test}" -o "${mapserver_body}" \
      && grep -qi '^Content-Type:[[:space:]]*image/png' "${mapserver_headers}" \
      && head -c 8 "${mapserver_body}" | od -An -t x1 | tr -d ' \n' | grep -q '^89504e470d0a1a0a$'; then
      mapserver_ok=true
      break
    fi
    sleep 2
  done
  if [[ "${mapserver_ok}" != true ]]; then
    echo "MapServer smoke test failed" >&2
    compose_cmd logs --tail 40 eafw_mapserver eafw_nginx || true
    return 1
  fi

  local mapcache_ok=false
  for _ in $(seq 1 6); do
    local mapcache_status
    mapcache_status="$(curl -sS -o /tmp/eafw-mapcache-smoke.txt -w '%{http_code}' --max-time 20 "${mapcache_test}" || true)"
    if [[ "${mapcache_status}" != "000" && "${mapcache_status}" != "502" && "${mapcache_status}" != "503" && "${mapcache_status}" != "504" ]] \
      && [[ -s /tmp/eafw-mapcache-smoke.txt ]]; then
      mapcache_ok=true
      break
    fi
    sleep 2
  done
  if [[ "${mapcache_ok}" != true ]]; then
    echo "MapCache smoke test failed" >&2
    compose_cmd logs --tail 40 eafw_mapcache eafw_nginx || true
    return 1
  fi

  log "Smoke tests passed"
}

main() {
  cd "${REPO_ROOT}"

  [[ "${DO_SYNC_MAPFILES}" == true ]] && sync_mapfiles
  [[ "${DO_CLEAR_MAPCACHE}" == true ]] && clear_mapcache
  [[ "${DO_RESTART}" == true ]] && restart_map_stack
  [[ "${DO_SMOKE_TEST}" == true ]] && smoke_test

  log "Map services maintenance completed"
}

main "$@"
