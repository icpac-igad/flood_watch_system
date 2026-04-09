# check=skip=SecretsUsedInArgOrEnv
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

# Clone geomanager-web from eafw branch
ARG GH_TOKEN=""
ARG GH_BRANCH=eafw
RUN git clone -b ${GH_BRANCH} --depth 1 \
    $(if [ -n "$GH_TOKEN" ]; then echo "https://${GH_TOKEN}@github.com/icpac-igad/geomanager-web.git"; else echo "https://github.com/icpac-igad/geomanager-web.git"; fi) \
    ${APP_HOME}

WORKDIR ${APP_HOME}
RUN uv venv ${APP_HOME}/.venv

# Configure git for private repos then install ALL deps
# No --mount=type=ssh — pure HTTPS with token (avoids BuildKit cache issues)
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

# Copy everything from builder (app code + .venv with all packages)
COPY --from=builder ${APP_HOME} ${APP_HOME}

ENV PATH=${APP_HOME}/.venv/bin:${PATH}

# Setup
ENV GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR=/geomanager/data
RUN mkdir -p $GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR && \
    cp docker/cms/docker-entrypoint.sh . && \
    chmod +x docker-entrypoint.sh && \
    mkdir -p tmp

EXPOSE 8000
