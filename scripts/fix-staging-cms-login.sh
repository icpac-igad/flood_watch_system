#!/bin/bash
# scripts/fix-staging-cms-login.sh
# Fixes CMS sign-in issue on staging caused by secure cookie settings over HTTP.
#
# Root cause: production.py sets SESSION_COOKIE_SECURE=True and CSRF_COOKIE_SECURE=True,
# which tells the browser to only send cookies over HTTPS. Staging uses HTTP,
# so the session cookie is never sent back — the user appears logged out immediately.
#
# This script patches the running container for an immediate fix, then optionally
# creates a superuser if none exists.
#
# Usage: bash scripts/fix-staging-cms-login.sh [--create-superuser]

set -euo pipefail

CMS_CONTAINER="${WEB_CNTR_NAME:-eafw-cms}"
SETTINGS_PATH="/opt/eafw_cms/geomanagerweb/settings/production.py"

echo "=== FloodWatch CMS Staging Login Fix ==="
echo ""

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CMS_CONTAINER}$"; then
    echo "ERROR: Container '${CMS_CONTAINER}' is not running."
    echo "Available containers:"
    docker ps --format '  {{.Names}} ({{.Status}})'
    exit 1
fi

echo "[1/4] Checking current cookie security settings..."
CURRENT=$(docker exec "$CMS_CONTAINER" grep -n "SESSION_COOKIE_SECURE\|CSRF_COOKIE_SECURE" "$SETTINGS_PATH" 2>/dev/null || true)
echo "  Current settings in container:"
echo "  $CURRENT"
echo ""

echo "[2/4] Patching cookie security settings for HTTP access..."
# Replace hardcoded True with False for HTTP staging
docker exec "$CMS_CONTAINER" sed -i \
    's/^SESSION_COOKIE_SECURE\s*=.*/SESSION_COOKIE_SECURE = False/' \
    "$SETTINGS_PATH"
docker exec "$CMS_CONTAINER" sed -i \
    's/^CSRF_COOKIE_SECURE\s*=.*/CSRF_COOKIE_SECURE = False/' \
    "$SETTINGS_PATH"

echo "  Patched settings:"
docker exec "$CMS_CONTAINER" grep -n "SESSION_COOKIE_SECURE\|CSRF_COOKIE_SECURE" "$SETTINGS_PATH"
echo ""

echo "[3/4] Checking for existing superusers..."
SUPERUSER_COUNT=$(docker exec "$CMS_CONTAINER" /opt/venv/bin/python manage.py shell -c \
    "from django.contrib.auth import get_user_model; User = get_user_model(); print(User.objects.filter(is_superuser=True).count())" 2>/dev/null)
echo "  Found $SUPERUSER_COUNT superuser(s)"

if [ "$SUPERUSER_COUNT" = "0" ] || [ "${1:-}" = "--create-superuser" ]; then
    echo ""
    echo "  Creating/resetting superuser..."
    echo "  Enter credentials for the CMS admin account:"
    read -rp "  Username [admin]: " SU_USERNAME
    SU_USERNAME="${SU_USERNAME:-admin}"
    read -rp "  Email [admin@floodwatch.icpac.net]: " SU_EMAIL
    SU_EMAIL="${SU_EMAIL:-admin@floodwatch.icpac.net}"
    read -rsp "  Password: " SU_PASSWORD
    echo ""

    if [ -z "$SU_PASSWORD" ]; then
        echo "  ERROR: Password cannot be empty."
        exit 1
    fi

    docker exec "$CMS_CONTAINER" /opt/venv/bin/python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
user, created = User.objects.get_or_create(username='${SU_USERNAME}', defaults={'email': '${SU_EMAIL}'})
user.set_password('${SU_PASSWORD}')
user.is_superuser = True
user.is_staff = True
user.is_active = True
user.email = '${SU_EMAIL}'
user.save()
print(f\"  {'Created' if created else 'Updated'} superuser: {user.username}\")
"
fi

echo ""
echo "[4/4] Restarting CMS container to apply changes..."
docker restart "$CMS_CONTAINER"

echo ""
echo "  Waiting for CMS to become healthy..."
for i in $(seq 1 30); do
    if docker exec "$CMS_CONTAINER" curl -sf http://localhost:8000/ > /dev/null 2>&1; then
        echo "  CMS is up and healthy!"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "  WARNING: CMS did not respond within 30s. Check logs: docker logs $CMS_CONTAINER"
        break
    fi
    sleep 2
done

echo ""
echo "=== Done! ==="
echo "You should now be able to sign in at the CMS admin panel."
echo ""
echo "NOTE: This is a runtime patch. It will be lost if the container is recreated."
echo "For a permanent fix, rebuild the CMS image with the updated production.py"
echo "that reads SESSION_COOKIE_SECURE and CSRF_COOKIE_SECURE from environment variables."
