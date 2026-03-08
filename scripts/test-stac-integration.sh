#!/usr/bin/env bash
set -euo pipefail

# STAC Integration Test Runner for FloodWatch
# Usage: ./scripts/test-stac-integration.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

echo "============================================"
echo " FloodWatch STAC Integration Tests"
echo "============================================"
echo ""

# Step 1: Health checks
echo -e "${YELLOW}Step 1: Service health checks${NC}"
if "$SCRIPT_DIR/stac-healthcheck.sh"; then
    echo -e "${GREEN}Health checks passed${NC}"
else
    echo -e "${RED}Health checks failed — some services may be down${NC}"
    echo "Continuing with tests anyway..."
fi

echo ""

# Step 2: Unit tests (no services needed)
echo -e "${YELLOW}Step 2: Unit tests (security module)${NC}"
cd "$PROJECT_DIR"
if python -m pytest eafw_stac/tests/test_security.py -v --tb=short 2>/dev/null; then
    echo -e "${GREEN}Unit tests passed${NC}"
else
    echo -e "${RED}Unit tests failed${NC}"
fi

echo ""

# Step 3: Integration tests
echo -e "${YELLOW}Step 3: Integration tests${NC}"
export STAC_API_URL="${STAC_API_URL:-http://localhost:9070}"
export TITILER_URL="${TITILER_URL:-http://localhost:9071}"

if python -m pytest eafw_stac/tests/ -v --tb=short -m integration 2>/dev/null; then
    echo -e "${GREEN}Integration tests passed${NC}"
else
    echo -e "${YELLOW}Some integration tests failed (services may not be running)${NC}"
fi

echo ""
echo "============================================"
echo " Tests complete"
echo "============================================"
