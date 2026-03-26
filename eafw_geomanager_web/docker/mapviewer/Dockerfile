# check=skip=SecretsUsedInArgOrEnv

# Stage 1: Build
FROM node:20-slim AS builder

RUN apt-get update && apt-get install -y \
    git \
    zlib1g-dev \
    libpng-dev \
    libgl1 \
    libxi6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp/geomapviewer

# Copy local geomapviewer source (build context is eafw_geomapviewer/)
COPY . .

# Env Variables that should be available at build time
ARG ANALYTICS_PROPERTY_ID
ARG DEBUG
ARG FEATURE_ENV
ARG BASE_PATH
ARG ASSET_PREFIX
ARG CMS_API
ARG GOOGLE_CUSTOM_SEARCH_CX
ARG BITLY_TOKEN
ARG GOOGLE_SEARCH_API_KEY
ARG ADMIN_BOUNDARY_API

# map viewport settings
ARG DEFAULT_CENTER_LAT=5.73
ARG DEFAULT_CENTER_LNG=36.84
ARG DEFAULT_ZOOM_LEVEL=4
ARG DEFAULT_MIN_ZOOM=4

# environment vars
ENV ANALYTICS_PROPERTY_ID=${ANALYTICS_PROPERTY_ID} DEBUG=${DEBUG} \
    FEATURE_ENV=${FEATURE_ENV} BASE_PATH=${BASE_PATH} CMS_API=${CMS_API} \
    ASSET_PREFIX=${ASSET_PREFIX}

# create .env file
RUN rm -f .env && \
    echo "ANALYTICS_PROPERTY_ID=${ANALYTICS_PROPERTY_ID}" >> .env && \
    echo "BITLY_TOKEN=${BITLY_TOKEN}" >> .env && \
    echo "GOOGLE_CUSTOM_SEARCH_CX=${GOOGLE_CUSTOM_SEARCH_CX}" >> .env && \
    echo "GOOGLE_SEARCH_API_KEY=${GOOGLE_SEARCH_API_KEY}" >> .env && \
    echo "BASE_PATH=${BASE_PATH}" >> .env && \
    echo "ASSET_PREFIX=${ASSET_PREFIX}" >> .env && \
    echo "CMS_API=${CMS_API}" >> .env && \
    echo "ADMIN_BOUNDARY_API=${ADMIN_BOUNDARY_API}" >> .env && \
    echo "DEFAULT_CENTER_LAT=${DEFAULT_CENTER_LAT}" >> .env && \
    echo "DEFAULT_CENTER_LNG=${DEFAULT_CENTER_LNG}" >> .env && \
    echo "DEFAULT_ZOOM_LEVEL=${DEFAULT_ZOOM_LEVEL}" >> .env && \
    echo "DEFAULT_MIN_ZOOM=${DEFAULT_MIN_ZOOM}" >> .env

# Install packages
RUN --mount=type=cache,target=/root/.yarn YARN_CACHE_FOLDER=/root/.yarn yarn --frozen-lockfile

# Build
RUN yarn build

# Stage 2: run
FROM node:20-slim

WORKDIR /app

COPY --from=builder /tmp/geomapviewer/.next ./.next
COPY --from=builder /tmp/geomapviewer/public ./public
COPY --from=builder /tmp/geomapviewer/node_modules ./node_modules
COPY --from=builder /tmp/geomapviewer/package.json ./

# Inline entrypoint
RUN echo '#!/bin/bash\nmkdir -p /app/nginx/.next\ncp -r /app/.next/. /app/nginx/.next/\nyarn start\nexec "$@"' > docker-entrypoint.sh && \
    chmod +x docker-entrypoint.sh

EXPOSE 3000
ENTRYPOINT ["./docker-entrypoint.sh"]
