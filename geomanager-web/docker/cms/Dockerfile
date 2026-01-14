# syntax = docker/dockerfile:1.5

ARG GDAL_VERSION=3.10.1
FROM ghcr.io/osgeo/gdal:ubuntu-small-${GDAL_VERSION} AS runner

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Africa/Nairobi

# install apt packages
RUN apt-get update && apt-get install -y \
    cron \
    git \
    libgeos-dev \
    imagemagick \
    libmagic1 \
    libcairo2-dev \
    libffi-dev \
    python3-pip \
    python3-venv \
    curl \
    --fix-missing \
    lsb-release

# for pg_dump
RUN echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
    && curl --silent https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - \
    && apt-get update \
    && apt-get install -y postgresql-client-15

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# docker-compose-wait
ADD https://github.com/ufoscout/docker-compose-wait/releases/download/2.12.0/wait /wait
RUN chmod +x /wait

# uv (fast python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV APP_HOME=/home/app
ENV UV_PROJECT_ENVIRONMENT=/opt/venv

# IMPORTANT: set workdir before dependency operations so paths match
WORKDIR $APP_HOME

# Add GitHub's host key for SSH operations (if needed)
RUN mkdir -p /root/.ssh && \
    ssh-keyscan github.com >> /root/.ssh/known_hosts

# Copy the geomanager and forecastmanager (project dependencies referenced in pyproject)
# These must be available to uv when it resolves local path dependencies
COPY ./geomanager /home/geomanager
COPY ./forecastmanager /home/forecastmanager

# Copy dependency files to leverage Docker cache
COPY ./geomanager-web/pyproject.toml ./geomanager-web/uv.lock ./geomanager-web/build-constraints.txt ./

# Install dependencies with SSH mount for any git deps.
# This installs the environment packages but not yet the project package
RUN --mount=type=ssh \
    uv sync --frozen --no-dev --no-install-project

# Copy remaining app source
COPY ./geomanager-web $APP_HOME

# Now install the project and ensure local editable packages get installed
RUN uv sync --frozen --no-dev

# Ensure gunicorn / uvicorn are available inside venv
RUN uv pip install --python $UV_PROJECT_ENVIRONMENT gunicorn uvicorn

# Ensure watchdog (watchmedo) is present if your entrypoint expects it
# (watchmedo comes from watchdog)
RUN uv pip install --python $UV_PROJECT_ENVIRONMENT watchdog

ENV GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR=/geomanager/data
RUN mkdir -p $GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR

# copy entrypoint (kept in project root)
COPY ./geomanager-web/docker/cms/docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

RUN mkdir -p tmp

EXPOSE 8000
