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
ENV UV_HTTP_TIMEOUT=120

# docker-compose-wait
ADD https://github.com/ufoscout/docker-compose-wait/releases/download/2.12.0/wait /wait
RUN chmod +x /wait

# uv (fast python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV APP_HOME=/opt/eafw_cms
ENV UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR $APP_HOME

# Add GitHub's host key for SSH operations (if needed)
RUN mkdir -p /root/.ssh && \
    ssh-keyscan github.com >> /root/.ssh/known_hosts

# Copy the geomanager package (local dependency)
COPY ./eafw_cms/geomanager /opt/geomanager

# Copy dependency files to leverage Docker cache
COPY ./eafw_cms/pyproject.toml ./eafw_cms/uv.lock ./eafw_cms/build-constraints.txt ./

# Install dependencies (not the project itself yet)
RUN --mount=type=ssh \
    uv sync --frozen --no-dev --no-install-project

# Copy remaining app source
COPY ./eafw_cms $APP_HOME

# Install the project and local editable packages
RUN uv sync --frozen --no-dev

# Ensure gunicorn / uvicorn are available inside venv
RUN uv pip install --python $UV_PROJECT_ENVIRONMENT gunicorn uvicorn

# Ensure watchdog (watchmedo) is present
RUN uv pip install --python $UV_PROJECT_ENVIRONMENT watchdog

ENV GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR=/geomanager/data
RUN mkdir -p $GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR

# copy entrypoint
COPY ./eafw_docker/cms/docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

RUN mkdir -p tmp

EXPOSE 8000
