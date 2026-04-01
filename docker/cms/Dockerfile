# --------- pip packages builder ---------
ARG GDAL_VERSION=3.10.2
FROM ghcr.io/osgeo/gdal:ubuntu-small-${GDAL_VERSION} AS builder

RUN apt-get update && apt-get install -y \
    git \
    curl \
    libgeos-dev \
    imagemagick \
    libmagic1 \
    libcairo2-dev \
    libffi-dev \
    lsb-release --fix-missing && \
    curl -LsSf https://astral.sh/uv/install.sh | sh

ARG APP_HOME=/home/app
ENV PATH=/root/.local/bin:${APP_HOME}/.venv/bin:${PATH}

RUN mkdir -p ${APP_HOME} && \
    uv venv ${APP_HOME}/.venv

# Copy the web project (geomanager + georeport installed from git via uv)
# Build context is repo root (.), so copy the CMS subdirectory
COPY ./eafw_geomanager_web ${APP_HOME}
WORKDIR ${APP_HOME}

# Private git deps: use GH_TOKEN (CI) or SSH agent (local)
ARG GH_TOKEN=""
ARG CACHEBUST=1
RUN --mount=type=ssh \
    echo "Cache bust: $CACHEBUST" && \
    if [ -n "$GH_TOKEN" ]; then \
      git config --global url."https://${GH_TOKEN}@github.com/".insteadOf "ssh://git@github.com/"; \
      git config --global url."https://${GH_TOKEN}@github.com/".insteadOf "git@github.com:"; \
    else \
      mkdir -p ~/.ssh && ssh-keyscan github.com >> ~/.ssh/known_hosts; \
    fi && \
    uv lock && \
    uv sync --all-extras --no-cache --no-install-project && \
    uv add gunicorn uvicorn && \
    git config --global --unset-all url."https://${GH_TOKEN}@github.com/".insteadOf 2>/dev/null || true

# use osgeo gdal ubuntu small 3.10 image.
ARG GDAL_VERSION=3.10.0
FROM ghcr.io/osgeo/gdal:ubuntu-small-${GDAL_VERSION} AS runnner

# install dependencies
RUN apt-get update && apt-get install -y \
    cron \
    gnupg2 \
    libgeos-dev \
    imagemagick \
    lsb-release \
    --fix-missing

# for pg_dump
RUN echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
    && cat /etc/apt/sources.list.d/pgdg.list \
    && curl --silent https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - \
    && apt-get update \
    && apt-get install -y postgresql-client-15

# set python env
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# install docker-compose wait
ADD https://github.com/ufoscout/docker-compose-wait/releases/download/2.12.0/wait /wait
RUN chmod +x /wait

# create app home dir
ENV APP_HOME=/home/app
RUN mkdir -p $APP_HOME

# setup working dir
WORKDIR ${APP_HOME}
COPY --from=builder ${APP_HOME} ${APP_HOME}

ENV PATH=${APP_HOME}/.venv/bin:${PATH}

# create autoingestion directory
ENV GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR=/geomanager/data
RUN mkdir -p $GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR

# copy entrypoint.sh
COPY ./docker/cms/docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

# create tmp dir for handling large django uploads
RUN mkdir -p tmp

# Port used by this container to serve HTTP.
EXPOSE 8000
# force rebuild Tue Mar 31 08:31:44 PM EAT 2026
