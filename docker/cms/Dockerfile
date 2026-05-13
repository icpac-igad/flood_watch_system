# check=skip=SecretsUsedInArgOrEnv
#
# CMS image — clones the three upstream repos at build time using refs
# pinned in docker-compose.yml. There are no submodule directories in
# the parent repo; the parent owns Docker orchestration only.
#
# Build args (set in docker-compose.yml under geomanager_web.build.args):
#   GEOMANAGER_WEB_REPO / GEOMANAGER_WEB_REF — the Wagtail/Django glue
#   GEOMANAGER_REPO     / GEOMANAGER_REF     — shared GeoManager Django app
#   GEOREPORT_REPO      / GEOREPORT_REF      — shared `hazard-georeport` package
#   GH_TOKEN — optional, needed only if the upstream repos are private

# --------- builder ---------
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

ARG GH_TOKEN=""
ARG GEOMANAGER_WEB_REPO=https://github.com/icpac-igad/geomanager-web.git
ARG GEOMANAGER_WEB_REF=eafw
ARG GEOMANAGER_REPO=https://github.com/icpac-igad/geomanager.git
ARG GEOMANAGER_REF=eafw
ARG GEOREPORT_REPO=https://github.com/icpac-igad/georeport.git
ARG GEOREPORT_REF=eafw

# Clone geomanager-web at the pinned ref. Token-rewrite the URL so private
# repos work without extra auth setup; no-op for already-public URLs.
RUN _AUTH_URL=$(echo "${GEOMANAGER_WEB_REPO}" | sed "s|https://github.com/|https://${GH_TOKEN}@github.com/|") && \
    git clone --depth 1 -b ${GEOMANAGER_WEB_REF} "$_AUTH_URL" ${APP_HOME}

WORKDIR ${APP_HOME}

# Rewrite geomanager-web's pyproject.toml so the two git-based deps
# (`geomanager`, `hazard-georeport`) honour the refs pinned in our
# docker-compose.yml. This is what lets *all three* upstream versions
# be visible in one YAML at the parent level.
RUN sed -i \
    -e "s|hazard-georeport = { git = \"https://github.com/icpac-igad/georeport.git\", branch = \"eafw\" }|hazard-georeport = { git = \"${GEOREPORT_REPO}\", branch = \"${GEOREPORT_REF}\" }|" \
    -e "s|geomanager = { git = \"ssh://git@github.com/icpac-igad/geomanager.git\", branch = \"eafw\" }|geomanager = { git = \"${GEOMANAGER_REPO}\", branch = \"${GEOMANAGER_REF}\" }|" \
    pyproject.toml

RUN uv venv ${APP_HOME}/.venv

# Configure git for private repos then install all deps. Pure HTTPS with
# token (avoids BuildKit SSH cache issues).
RUN if [ -n "$GH_TOKEN" ]; then \
      git config --global url."https://${GH_TOKEN}@github.com/".insteadOf "https://github.com/"; \
      git config --global --add url."https://${GH_TOKEN}@github.com/".insteadOf "ssh://git@github.com/"; \
    fi && \
    uv lock && \
    uv sync --all-extras --no-cache --no-install-project && \
    uv add gunicorn uvicorn && \
    (git config --global --unset-all url."https://${GH_TOKEN}@github.com/".insteadOf 2>/dev/null || true)


# --------- runner ---------
ARG GDAL_VERSION=3.10.2
FROM ghcr.io/osgeo/gdal:ubuntu-small-${GDAL_VERSION} AS runner

RUN apt-get update && apt-get install -y \
    cron \
    gnupg2 \
    libgeos-dev \
    imagemagick \
    gettext \
    lsb-release \
    --fix-missing

# for pg_dump
RUN echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
    && curl --silent https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - \
    && apt-get update \
    && apt-get install -y postgresql-client-15

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

ADD https://github.com/ufoscout/docker-compose-wait/releases/download/2.12.0/wait /wait
RUN chmod +x /wait

ENV APP_HOME=/home/app
RUN mkdir -p $APP_HOME
WORKDIR ${APP_HOME}

# App code + .venv (from the cloned geomanager-web + installed deps)
COPY --from=builder ${APP_HOME} ${APP_HOME}

# Entrypoint + backup cron come from the parent's docker/cms/ build context,
# not from inside geomanager-web. Parent owns Docker orchestration.
COPY docker-entrypoint.sh ${APP_HOME}/docker-entrypoint.sh
COPY backup.cron ${APP_HOME}/backup.cron

ENV PATH=${APP_HOME}/.venv/bin:${PATH}

ENV GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR=/geomanager/data
RUN mkdir -p $GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR && \
    chmod +x docker-entrypoint.sh && \
    mkdir -p tmp

EXPOSE 8000
