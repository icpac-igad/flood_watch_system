# Future Microservices Proposal

## Goal

Move away from a monolithic CMS-centered runtime and separate the platform into clear domain services with explicit ownership.

## Proposed Services

### 1. `eafw_cms`

- Owns Wagtail pages, editorial content, homepage layout, branding, media, navigation, and site settings.
- Should act as a presentation/composition layer.
- Should not own flood forecast business logic or geospatial ingestion logic.

### 2. `geomanager`

- Owns geospatial catalog, datasets, layers, boundaries, map configuration, and ingestion controls.
- Exposes dataset and layer APIs used by the CMS and map frontend.
- Should be deployable independently from the CMS.

### 3. `flood-api`

- Owns operational forecast and analytics APIs.
- Covers multimodal summaries, provider-specific forecast GeoJSON, country summaries, situation summaries, and time-series endpoints.
- Reads forecast stores directly and exposes stable HTTP contracts for the frontend and CMS.

### 4. `eafw_jobs`

- Owns scheduled ingestion and synchronization jobs.
- Pulls data from FTP, Google Flood API, cloud storage, and other providers.
- Writes into the forecast/geodata stores owned by `flood-api` and `geomanager`.

### 5. Tile / Rendering Services

- `mapserver`
- `mapcache`
- `pg_tileserv`

These should remain infrastructure/data-serving services, not application-logic owners.

## Recommended Ownership Rules

- CMS owns content.
- Geomanager owns catalog and map metadata.
- Flood API owns forecast query logic and provider-specific output shaping.
- Jobs own ingestion only.
- Frontends consume APIs; they should not embed backend rules.

## Migration Principles

1. Stop runtime Python coupling between CMS and geomanager.
2. Move forecast/business APIs out of CMS into `flood-api`.
3. Keep CMS responsible for presentation and composition only.
4. Introduce service-specific databases or at least service-specific schema ownership.
5. Use an nginx/API gateway layer for routing across services.

## Near-Term Practical Shape

- `eafw_cms`: pages and homepage shell
- `geomanager`: datasets, categories, map config, boundaries
- `flood-api`: multimodal, Google Flood, FloodProofs, GeoSFM, Mike Hydro, WRF support APIs
- `eafw_jobs`: sync and ingest workers
- `geomapviewer`: frontend client

## Why This Is Better

- Reduces hidden coupling between editorial code and forecast logic.
- Makes forecast/provider APIs easier to evolve independently.
- Keeps geomanager reusable outside the CMS.
- Makes jobs and runtime services easier to deploy, test, and scale separately.
