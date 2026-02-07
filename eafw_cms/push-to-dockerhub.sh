#!/bin/bash
# Script to push FloodWatch images to Docker Hub for staging deployment
# Run this on your DEVELOPMENT server

set -e

# ============================================
# CONFIGURATION - UPDATE THESE
# ============================================
DOCKERHUB_USERNAME="hkoros"  # Your Docker Hub username
VERSION="v1.0.1"             # Version tag
REPO_WEB="eafw-cms-web"      # CMS image name
REPO_UI="eafw-mapviewer"     # UI image name
REPO_JOBS="eafw-floodwatch-jobs"  # Jobs scheduler image name

echo "🐳 FloodWatch - Docker Hub Push Script"
echo "======================================"
echo "Docker Hub Username: ${DOCKERHUB_USERNAME}"
echo "Version: ${VERSION}"
echo ""

# Check if already logged in
if ! docker info | grep -q "Username: ${DOCKERHUB_USERNAME}"; then
    echo "🔐 Please login to Docker Hub..."
    docker login
fi

cd /home/koros/IGAD-ICPAC/Projects/FloodWatch/code/hazard_watch/geomanager-web

# ============================================
# BUILD PRODUCTION IMAGES
# ============================================
echo ""
echo "🏗️  Building production images..."
echo "This will take 10-20 minutes..."
echo ""

# Set production build args
export DJANGO_SETTINGS_MODULE=geomanagerweb.settings.production

# Build CMS image
echo "📦 Building CMS (geomanager-web) image..."
docker compose build geomanager_web

# Build MapViewer image
echo "📦 Building MapViewer (geomapviewer) image..."
docker compose build geomanager_mapviewer

# Build FloodWatch Jobs image
echo "📦 Building FloodWatch Jobs (floodwatch-jobs) image..."
docker compose build floodwatch_jobs

echo "✅ Images built successfully!"

# ============================================
# TAG IMAGES FOR DOCKER HUB
# ============================================
echo ""
echo "🏷️  Tagging images for Docker Hub..."

# Get local image names from docker compose
LOCAL_WEB_IMAGE=$(docker compose config --images | grep cms-web || echo "icpac/eafw-cms-web:v1.0.0")
LOCAL_UI_IMAGE=$(docker compose config --images | grep mapviewer || echo "icpac/eafw-mapviewer:v1.0.0")
LOCAL_JOBS_IMAGE=$(docker compose config --images | grep jobs || echo "icpac/eafw-floodwatch-jobs:v1.0.0")

# Tag CMS image
docker tag ${LOCAL_WEB_IMAGE} ${DOCKERHUB_USERNAME}/${REPO_WEB}:${VERSION}

# Tag UI image
docker tag ${LOCAL_UI_IMAGE} ${DOCKERHUB_USERNAME}/${REPO_UI}:${VERSION}

# Tag Jobs image
docker tag ${LOCAL_JOBS_IMAGE} ${DOCKERHUB_USERNAME}/${REPO_JOBS}:${VERSION}

echo "✅ Images tagged:"
echo "   - ${DOCKERHUB_USERNAME}/${REPO_WEB}:${VERSION}"
echo "   - ${DOCKERHUB_USERNAME}/${REPO_UI}:${VERSION}"
echo "   - ${DOCKERHUB_USERNAME}/${REPO_JOBS}:${VERSION}"

# ============================================
# PUSH TO DOCKER HUB
# ============================================
echo ""
echo "📤 Pushing images to Docker Hub..."
echo "This will take 20-60 minutes depending on your internet speed..."
echo ""

# Push CMS images
echo "⬆️  Pushing CMS image..."
docker push ${DOCKERHUB_USERNAME}/${REPO_WEB}:${VERSION}

# Push UI images
echo "⬆️  Pushing UI image..."
docker push ${DOCKERHUB_USERNAME}/${REPO_UI}:${VERSION}

# Push Jobs images
echo "⬆️  Pushing Jobs image..."
docker push ${DOCKERHUB_USERNAME}/${REPO_JOBS}:${VERSION}

echo ""
echo "✅ =========================================="
echo "✅ IMAGES PUSHED TO DOCKER HUB SUCCESSFULLY!"
echo "✅ =========================================="
echo ""
echo "📍 Docker Hub URLs:"
echo "   CMS:       https://hub.docker.com/r/${DOCKERHUB_USERNAME}/${REPO_WEB}"
echo "   MapViewer: https://hub.docker.com/r/${DOCKERHUB_USERNAME}/${REPO_UI}"
echo "   Jobs:      https://hub.docker.com/r/${DOCKERHUB_USERNAME}/${REPO_JOBS}"
echo ""
echo "🎯 Next Steps:"
echo "   1. Backup database: bash backup-for-staging.sh"
echo "   2. SCP files to staging server"
echo "   3. Deploy on staging: docker compose pull && docker compose up -d"
echo ""
