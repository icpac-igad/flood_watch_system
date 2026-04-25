# check=skip=SecretsUsedInArgOrEnv
# syntax=docker/dockerfile:1.6
#
# Three-stage build:
#   1. deps     — yarn install, cached on package.json/yarn.lock only.
#   2. builder  — copies source, runs `yarn build` with a persistent
#                 .next/cache mount for incremental compiles.
#   3. runtime  — slim image using Next.js standalone output (~300 MB
#                 instead of 1.4 GB).
#
# Source-only changes reuse the deps layer, keeping warm rebuilds under a
# minute.

# ── Stage 0: base with native libs (shared by deps + builder) ───────────────
# cwebp/webp-loader needs libGL at build time; native npm modules need the
# toolchain. We install once here so both subsequent stages inherit.
FROM node:20-slim AS base
RUN apt-get update && apt-get install -y --no-install-recommends \
      git zlib1g-dev libpng-dev libgl1 libxi6 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /tmp/geomapviewer


# ── Stage 1: dependencies ────────────────────────────────────────────────────
FROM base AS deps
COPY package.json yarn.lock ./
RUN --mount=type=cache,target=/root/.yarn \
    YARN_CACHE_FOLDER=/root/.yarn \
    yarn install --frozen-lockfile


# ── Stage 2: build ───────────────────────────────────────────────────────────
FROM base AS builder

COPY --from=deps /tmp/geomapviewer/node_modules ./node_modules

# Build-time ARGs (unchanged semantics from the previous Dockerfile)
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
ARG DEFAULT_CENTER_LAT=5.73
ARG DEFAULT_CENTER_LNG=36.84
ARG DEFAULT_ZOOM_LEVEL=4
ARG DEFAULT_MIN_ZOOM=0

ENV ANALYTICS_PROPERTY_ID=${ANALYTICS_PROPERTY_ID} DEBUG=${DEBUG} \
    FEATURE_ENV=${FEATURE_ENV} BASE_PATH=${BASE_PATH} CMS_API=${CMS_API} \
    ASSET_PREFIX=${ASSET_PREFIX}

COPY . .

RUN rm -f .env && { \
      echo "ANALYTICS_PROPERTY_ID=${ANALYTICS_PROPERTY_ID}"; \
      echo "BITLY_TOKEN=${BITLY_TOKEN}"; \
      echo "GOOGLE_CUSTOM_SEARCH_CX=${GOOGLE_CUSTOM_SEARCH_CX}"; \
      echo "GOOGLE_SEARCH_API_KEY=${GOOGLE_SEARCH_API_KEY}"; \
      echo "BASE_PATH=${BASE_PATH}"; \
      echo "ASSET_PREFIX=${ASSET_PREFIX}"; \
      echo "CMS_API=${CMS_API}"; \
      echo "ADMIN_BOUNDARY_API=${ADMIN_BOUNDARY_API}"; \
      echo "DEFAULT_CENTER_LAT=${DEFAULT_CENTER_LAT}"; \
      echo "DEFAULT_CENTER_LNG=${DEFAULT_CENTER_LNG}"; \
      echo "DEFAULT_ZOOM_LEVEL=${DEFAULT_ZOOM_LEVEL}"; \
      echo "DEFAULT_MIN_ZOOM=${DEFAULT_MIN_ZOOM}"; \
    } > .env

# Persist Next.js's own incremental compile cache across builds.
RUN --mount=type=cache,target=/tmp/geomapviewer/.next/cache yarn build


# ── Stage 3: runtime ────────────────────────────────────────────────────────
FROM node:20-slim AS runtime

WORKDIR /app
ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# Next.js standalone ships its own minimal node_modules + server.js.
COPY --from=builder /tmp/geomapviewer/.next/standalone ./
COPY --from=builder /tmp/geomapviewer/.next/static    ./.next/static
COPY --from=builder /tmp/geomapviewer/public          ./public

# Seed /app/nginx/.next/static on startup — compose mounts that path as the
# shared eafw_mapviewer_static volume so nginx can serve /_next/static/*
# directly (fast static-file path) while Next.js serves SSR + _next/data.
RUN printf '#!/bin/sh\nset -e\nmkdir -p /app/nginx/.next/static\ncp -r /app/.next/static/. /app/nginx/.next/static/ 2>/dev/null || true\nexec node server.js\n' > /app/docker-entrypoint.sh && \
    chmod +x /app/docker-entrypoint.sh

EXPOSE 3000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
