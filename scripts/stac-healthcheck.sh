#!/usr/bin/env bash
set -euo pipefail

# STAC Services Health Check for FloodWatch
# Usage: ./scripts/stac-healthcheck.sh [--verbose]

BASE_URL="${STAC_BASE_URL:-http://localhost:9068}"
STAC_API_PATH="${STAC_API_PATH:-/stac-browser/api}"
STAC_BROWSER_PATH="${STAC_BROWSER_PATH:-/stac-browser}"
TITILER_PATH="${TITILER_PATH:-/cog-tiles}"
VERBOSE="${1:-}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

PASSED=0
FAILED=0

check_service() {
    local name="$1"
    local url="$2"
    local expected_code="${3:-200}"

    if [[ "$VERBOSE" == "--verbose" ]]; then
        echo -n "  Checking $name ($url)... "
    else
        echo -n "  $name... "
    fi

    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "$url" 2>/dev/null || echo "000")

    if [[ "$HTTP_CODE" == "$expected_code" ]]; then
        echo -e "${GREEN}OK${NC} ($HTTP_CODE)"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}FAIL${NC} (got $HTTP_CODE, expected $expected_code)"
        FAILED=$((FAILED + 1))
    fi
}

echo "============================================"
echo " FloodWatch STAC Health Check"
echo " Base URL: $BASE_URL"
echo "============================================"
echo ""

echo "Core Services:"
check_service "STAC API" "$BASE_URL${STAC_API_PATH}/"
check_service "TiTiler" "$BASE_URL${TITILER_PATH}/healthz"
check_service "STAC Browser" "$BASE_URL${STAC_BROWSER_PATH}/"

echo ""
echo "STAC API Endpoints:"
check_service "Collections" "$BASE_URL${STAC_API_PATH}/collections"
check_service "Search (GET)" "$BASE_URL${STAC_API_PATH}/search"

echo ""
echo "Existing Services:"
check_service "FloodWatch API" "$BASE_URL/health"
check_service "MapCache" "$BASE_URL/mapcache/"

echo ""
echo "============================================"
if [[ "$FAILED" -eq 0 ]]; then
    echo -e " Result: ${GREEN}ALL HEALTHY${NC} ($PASSED passed)"
    exit 0
else
    echo -e " Result: ${RED}$FAILED FAILED${NC}, $PASSED passed"
    exit 1
fi
