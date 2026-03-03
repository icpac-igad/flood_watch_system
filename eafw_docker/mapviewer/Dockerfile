# syntax = docker/dockerfile:1.5

#############################################
# Stage 1 – Build Next.js App
#############################################
FROM node:20-bookworm-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    zlib1g-dev \
    libpng-dev \
    libgl1 \
    libxi6 \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy full geomapviewer source (trailing slash important)
COPY eafw_mapviewer/ ./

# Copy entrypoint (optional if you want it in build stage)
COPY eafw_docker/mapviewer/docker-entrypoint.sh ./docker-entrypoint.sh
RUN chmod +x docker-entrypoint.sh

# Build-time ENV (from docker-compose build args)
ARG ANALYTICS_PROPERTY_ID
ARG BITLY_TOKEN
ARG DEBUG
ARG FEATURE_ENV
ARG GOOGLE_CUSTOM_SEARCH_CX
ARG GOOGLE_SEARCH_API_KEY
ARG BASE_PATH
ARG ASSET_PREFIX
ARG CMS_API
ARG ADMIN_BOUNDARY_API

ENV ANALYTICS_PROPERTY_ID=$ANALYTICS_PROPERTY_ID
ENV BITLY_TOKEN=$BITLY_TOKEN
ENV DEBUG=$DEBUG
ENV FEATURE_ENV=$FEATURE_ENV
ENV GOOGLE_CUSTOM_SEARCH_CX=$GOOGLE_CUSTOM_SEARCH_CX
ENV GOOGLE_SEARCH_API_KEY=$GOOGLE_SEARCH_API_KEY
ENV BASE_PATH=$BASE_PATH
ENV ASSET_PREFIX=$ASSET_PREFIX
ENV CMS_API=$CMS_API
ENV ADMIN_BOUNDARY_API=$ADMIN_BOUNDARY_API

# Dynamically create .env file
RUN rm -f .env && \
    echo "ANALYTICS_PROPERTY_ID=$ANALYTICS_PROPERTY_ID" >> .env && \
    echo "BITLY_TOKEN=$BITLY_TOKEN" >> .env && \
    echo "GOOGLE_CUSTOM_SEARCH_CX=$GOOGLE_CUSTOM_SEARCH_CX" >> .env && \
    echo "GOOGLE_SEARCH_API_KEY=$GOOGLE_SEARCH_API_KEY" >> .env && \
    echo "BASE_PATH=$BASE_PATH" >> .env && \
    echo "ASSET_PREFIX=$ASSET_PREFIX" >> .env && \
    echo "CMS_API=$CMS_API" >> .env && \
    echo "ADMIN_BOUNDARY_API=$ADMIN_BOUNDARY_API" >> .env

# Install JS dependencies (no cache - fresh install)
RUN yarn --frozen-lockfile

# Build Next.js for production
RUN yarn build

#############################################
# Stage 2 – Runtime Image
#############################################
FROM node:20-bookworm-slim

WORKDIR /app

# Copy artifacts from builder
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/src/content ./src/content
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./

# Copy entrypoint script
COPY eafw_docker/mapviewer/docker-entrypoint.sh ./docker-entrypoint.sh
RUN chmod +x docker-entrypoint.sh

# Expose port if needed
EXPOSE 3000

# Run the entrypoint
ENTRYPOINT ["./docker-entrypoint.sh"]
