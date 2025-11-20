#!/bin/bash
set -e

# FloodWatch Docker Build and Push Script
# Rebuilds all custom images and pushes to Docker Hub (hkoros)
# Uses tags from docker-compose.yml

echo "=========================================="
echo "FloodWatch Docker Build & Push"
echo "=========================================="
echo ""

# Check if logged into Docker Hub
if ! docker info | grep -q "Username"; then
    echo "⚠️  Not logged into Docker Hub. Please run: docker login"
    read -p "Press Enter to continue if already logged in, or Ctrl+C to abort..."
fi

# Image tag version (from docker-compose.yml)
VERSION="1.1.0"
DOCKER_USER="hkoros"

# Build timestamp for tracking
BUILD_TIME=$(date -u +"%Y-%m-%d %H:%M:%S UTC")

# Function to build and push an image
build_and_push() {
    local SERVICE_NAME=$1
    local CONTEXT=$2
    local DOCKERFILE=$3
    local IMAGE_NAME="${DOCKER_USER}/floodwatch-${SERVICE_NAME}:${VERSION}"
    local BUILD_ARGS=$4

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📦 Building: ${IMAGE_NAME}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Context: ${CONTEXT}"
    echo "Dockerfile: ${DOCKERFILE}"
    echo ""

    # Build the image
    if [ -n "$BUILD_ARGS" ]; then
        docker build $BUILD_ARGS -t "${IMAGE_NAME}" -f "${CONTEXT}/${DOCKERFILE}" "${CONTEXT}"
    else
        docker build -t "${IMAGE_NAME}" -f "${CONTEXT}/${DOCKERFILE}" "${CONTEXT}"
    fi

    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ Build successful: ${IMAGE_NAME}"
        echo ""
        echo "🚀 Pushing to Docker Hub..."
        docker push "${IMAGE_NAME}"

        if [ $? -eq 0 ]; then
            echo "✅ Push successful: ${IMAGE_NAME}"
        else
            echo "❌ Push failed: ${IMAGE_NAME}"
            return 1
        fi
    else
        echo "❌ Build failed: ${IMAGE_NAME}"
        return 1
    fi
}

# Track build status
FAILED_BUILDS=()
SUCCESSFUL_BUILDS=()

echo "Starting builds at ${BUILD_TIME}"
echo ""

# Build Backend (Django + Celery)
echo "[1/4] Backend Service"
if build_and_push "backend" "./backend" "Dockerfile"; then
    SUCCESSFUL_BUILDS+=("backend")
else
    FAILED_BUILDS+=("backend")
fi

# Build Frontend (React + Vite)
echo ""
echo "[2/4] Frontend Service"
if build_and_push "frontend" "./frontend" "Dockerfile" "--target production"; then
    SUCCESSFUL_BUILDS+=("frontend")
else
    FAILED_BUILDS+=("frontend")
fi

# Build FastAPI
echo ""
echo "[3/4] FastAPI Service"
if build_and_push "fastapi" "./fastapi-service" "Dockerfile"; then
    SUCCESSFUL_BUILDS+=("fastapi")
else
    FAILED_BUILDS+=("fastapi")
fi

# Build TiPg (Vector Tiles)
echo ""
echo "[4/4] TiPg Service"
if build_and_push "tipg" "./tipg-service" "Dockerfile"; then
    SUCCESSFUL_BUILDS+=("tipg")
else
    FAILED_BUILDS+=("tipg")
fi

# Summary
echo ""
echo "=========================================="
echo "BUILD & PUSH SUMMARY"
echo "=========================================="
echo ""
echo "Successful builds (${#SUCCESSFUL_BUILDS[@]}):"
for img in "${SUCCESSFUL_BUILDS[@]}"; do
    echo "  ✅ floodwatch-${img}:${VERSION}"
done

if [ ${#FAILED_BUILDS[@]} -gt 0 ]; then
    echo ""
    echo "Failed builds (${#FAILED_BUILDS[@]}):"
    for img in "${FAILED_BUILDS[@]}"; do
        echo "  ❌ floodwatch-${img}:${VERSION}"
    done
    echo ""
    echo "⚠️  Some builds failed. Please check the errors above."
    exit 1
else
    echo ""
    echo "🎉 All images built and pushed successfully!"
    echo ""
    echo "To deploy the new images, run:"
    echo "  docker-compose pull"
    echo "  docker-compose up -d"
fi

echo ""
echo "=========================================="
