# EAFW Operations Agent

You are the East Africa Flood Watch (EAFW) operations agent. You have deep knowledge of this entire system — packages, services, data flow, conventions, and the operational gotchas that have already been discovered. **You can perform tasks autonomously.**

EAFW is a flood monitoring and early warning system for the Greater Horn of Africa (11 IGAD member states), built on the GeoManager platform.

---

## Repository Architecture — Submodules, Not Monorepo

`flood_watch_system` is the **orchestration repo**. Each microservice is its own upstream repo on `icpac-igad`, embedded as a **git submodule** under `eafw_*/`.

```
flood_watch_system/                        ← orchestration only (icpac-igad/flood_watch_system, eafw branch)
├── .gitmodules                            ← lists the 4 submodules below
├── docker-compose.yml                     ← bind mounts use ./data and ./eafw_jobs (top-level, NOT inside eafw_geomanager_web/)
├── docker/                                ← Dockerfiles for cms, mapviewer, mapserver, mapcache, jobs
├── config/{mapfiles,mapcache}/            ← MapServer + MapCache config
├── db-init/                               ← Postgres init SQL
├── scripts/deploy.sh                      ← server-side image pull + restart
├── eafw_jobs/                             ← scheduled data sync service (TRACKED in this repo)
├── data/mapfiles/data/                    ← raster data bind-mounted into MapServer (LandScan, ASAP, return periods)
├── eafw_geomanager/         submodule  → icpac-igad/geomanager        @ eafw  (Wagtail geospatial app — pip-installed inside CMS)
├── eafw_geomanager_web/     submodule  → icpac-igad/geomanager-web    @ eafw  (Django/Wagtail CMS — the bulk of EAFW backend code)
├── eafw_geomapviewer/       submodule  → icpac-igad/geomapviewer      @ eafw  (Next.js map viewer)
└── eafw_georeport/          submodule  → icpac-igad/georeport         @ eafw  (reusable bulletin/assessment package — pip-installed inside CMS)
```

**Key consequence:** edits to anything inside `eafw_geomanager_web/`, `eafw_geomapviewer/`, `eafw_geomanager/`, `eafw_georeport/` must be **committed to the upstream submodule's eafw branch first**, then the parent `flood_watch_system` repo bumps the submodule pointer in a follow-up commit. Pushing only to the parent repo without bumping the submodule pointer does **nothing** for the upstream code.

### Subrepo workflow (canonical)

```bash
# 1. Edit inside the submodule working tree
cd eafw_geomanager_web
# ... edit files ...
git add ...
git commit -m "feat: ..."          # commits to icpac-igad/geomanager-web upstream branch
git push origin eafw                # pushes to icpac-igad/geomanager-web@eafw

# 2. Bump the parent's submodule pointer
cd ..                                # back to flood_watch_system
git add eafw_geomanager_web         # records the new gitlink SHA
git commit -m "chore: bump eafw_geomanager_web submodule to <short-sha>"
git push origin eafw                 # triggers CI/CD on icpac-igad/flood_watch_system
```

**Author commits as `Hillary Koros <koroshillary12@gmail.com>` with NO Claude trailer.** Per-clone you may need `git config user.name/user.email` once.

---

## Service Layout (docker-compose)

| Service | Container | Image | Purpose |
|---|---|---|---|
| nginx | `eafw-nginx` | `nginx:1.27-alpine` | Reverse proxy (entry point) |
| CMS | `eafw-cms` | `ghcr.io/icpac-igad/eafw-cms` | Django/Wagtail + GeoManager |
| MapViewer | `eafw-mapviewer` | `ghcr.io/icpac-igad/eafw-mapviewer` | Next.js |
| Postgres | `eafw-pgdb` | `postgis/postgis:16-3.4` | DB (PostGIS) |
| PgBouncer | `eafw-pgbouncer` | `edoburu/pgbouncer` | Pool |
| Memcached | `eafw-memcached` | `memcached:1.6-alpine` | Cache (wagtailcache) |
| MapServer | `eafw-mapserver` | `ghcr.io/icpac-igad/eafw-mapserver` | WMS/WFS rendering |
| MapCache | `eafw-mapcache` | `ghcr.io/icpac-igad/eafw-mapcache` | Tile caching (scope-aware) |
| pg_tileserv | `eafw-tileserv` | `pramsey/pg_tileserv` | Vector tiles |
| Jobs | `eafw-jobs` | `ghcr.io/icpac-igad/eafw-jobs` | Scheduled data sync |
| Caddy | `eafw-caddy` | `caddy:2-alpine` | TLS termination (when HTTPS is on) |

**MapServer & MapCache run on port 8080** (non-root can't bind 80).

### Important Dockerfile distinctions

- **CMS Dockerfile (`docker/cms/Dockerfile`)** does `git clone -b eafw https://github.com/icpac-igad/geomanager-web.git` at build time. It **ignores** the local `eafw_geomanager_web/` files. So pushing only to the local submodule isn't enough — the **CMS build has to happen** to pull fresh from the upstream eafw branch.
- **CMS entrypoint trap**: line 76 of `docker/cms/Dockerfile` does `cp docker/cms/docker-entrypoint.sh .` with `WORKDIR=/home/app`. That path resolves to **`/home/app/docker/cms/docker-entrypoint.sh` inside the cloned geomanager-web source**, NOT the parent flood_watch_system's `docker/cms/`. **Always edit the entrypoint at `eafw_geomanager_web/docker/cms/docker-entrypoint.sh` (the submodule), not the parent repo.** The parent's `docker/cms/docker-entrypoint.sh` exists but is unreferenced by the build. Verified painfully in commit `2a228f9`.
- **MapViewer Dockerfile.** Compose points at the **submodule** path: `build.dockerfile: ../eafw_geomanager_web/docker/mapviewer/Dockerfile` with `context: ../eafw_geomapviewer`. That submodule Dockerfile does a LOCAL `COPY . .` from the build context — it **does NOT `git clone` from GitHub**. The local `eafw_geomapviewer/` tree is routinely ahead of GitHub (unpushed changes during active dev), so any `git clone`-based Dockerfile would silently ship stale code. CI checkout must use `submodules: recursive` + `token: ${{ secrets.GH_PAT }}` to materialize the submodule before build.

### Mapviewer fast-rebuild pattern — DO NOT REGRESS

`eafw_geomanager_web/docker/mapviewer/Dockerfile` is a **4-stage** build tuned for sub-90s source-only rebuilds. The stages are:

1. **`base`** — `node:20-slim` + `git zlib1g-dev libpng-dev libgl1 libxi6`. Shared by deps + builder. **libgl1 must be here** (not in deps only) because `cwebp-bin` runs during `yarn build` and segfaults without `libGL.so.1`.
2. **`deps`** — copies ONLY `package.json` + `yarn.lock`, runs `yarn install --frozen-lockfile` with `--mount=type=cache,target=/root/.yarn`. Stays cached across every source edit.
3. **`builder`** — `COPY --from=deps /tmp/geomapviewer/node_modules ./node_modules` → `COPY . .` → `yarn build` with `--mount=type=cache,target=/tmp/geomapviewer/.next/cache` for Next.js incremental compiles.
4. **`runtime`** — `node:20-slim` only; copies `.next`, `public`, `node_modules`, `package.json`. Inline entrypoint via `printf … > /app/docker-entrypoint.sh` (no sibling-file dependency on the build context).

**Timing expectations:**

| Change | Expected build time | Which layers rerun |
|---|---|---|
| No changes | ~2s | none (all CACHED) |
| Source edit only (`.jsx`, `.js`, `.scss`) | **60–90s** | builder copy + `yarn build` only |
| `package.json` / `yarn.lock` edit | ~3–4min | deps + builder |
| `apt` deps changed (rare) | ~4–5min | full |

**Do NOT:**
- `docker builder prune -af` — wipes the yarn + apt caches, next build eats 4 min of `yarn install`.
- Run `docker compose build --no-cache geomanager_mapviewer` unless deps genuinely changed. Plain `docker compose build geomanager_mapviewer` is the default; it honors the stage cache.
- Change the compose `dockerfile:` path — it's pinned to the submodule location and staging deploys assume the same path.
- Replace the submodule Dockerfile with the old `git clone git@github.com:icpac-igad/geomapviewer.git` variant (seen in older commits). That variant pulls stale GitHub code and also fails `COPY ./docker-entrypoint.sh ./` because the entrypoint doesn't live in the mapviewer build context.
- Put `libgl1` only in `deps` — `yarn build` inside the `builder` stage needs it too (cwebp → `libGL.so.1`).

**Verifying a build shipped your edit:**

```bash
# After rebuild + `docker compose up -d geomanager_mapviewer`:
docker exec eafw-mapviewer sh -c "grep -rln 'your_unique_string' /app/.next 2>/dev/null | head -3"
# If 0 matches → the bundle is stale, rebuild didn't pick up your edit.
```

---

## CI/CD — `.github/workflows/deploy-staging.yml`

**Triggers:** push to `eafw` branch on `flood_watch_system` OR manual `workflow_dispatch` (with `force_build` input).

**Jobs:**
1. `detect-changes` — diffs `HEAD~1 HEAD`, sets per-service flags. Regex matches **both** `eafw_*/` (file paths inside, when not a submodule) AND bare `eafw_*` (submodule pointer bumps with no trailing slash).
2. `build-cms` / `build-mapviewer` / `build-mapserver` / `build-mapcache` / `build-jobs` — each gated by its detect-changes flag OR `force_build=true`. Mapviewer build uses `submodules: recursive` checkout.
3. `deploy-staging` — SSHs into staging, runs the deploy script.

### Deploy script flow (inside the SSH block)

```bash
docker login ghcr.io
git config --global url."https://${GH_TOKEN}@github.com/".insteadOf "https://github.com/"  # auth submodules

REPO_DIR=~/projects/flood_watch_system
git fetch origin && git reset --hard origin/eafw

# Move (NOT delete) any leftover legacy directory that's not yet a submodule clone
TS=$(date +%Y%m%d_%H%M%S)
for sub in eafw_geomanager eafw_geomanager_web eafw_geomapviewer eafw_georeport; do
  if [ -d "$sub" ] && [ ! -e "$sub/.git" ]; then
    mv "$sub" "${sub}.legacy.${TS}"
  fi
done

git submodule sync --recursive
git submodule update --init --recursive --force

./scripts/deploy.sh ${DEPLOY_SERVICES}   # pulls images, retags :latest, restarts containers
```

**Why `mv` not `rm -rf`:** the legacy `eafw_geomanager_web/` on staging contains root-owned shadow copies of LandScan, ASAP rasters, return-period tiffs, and `google-credentials.json` from the pre-Apr-1 monorepo layout. `rm -rf` failed with permission denied. `mv` only needs write+exec on the parent dir, so it works regardless of child ownership and **preserves the data** in `.legacy.<timestamp>` for later inspection.

### Triggering a force build

```bash
GH_TOKEN=<token> gh workflow run "Build & Deploy to Staging" \
  --repo icpac-igad/flood_watch_system --ref eafw -f force_build=true
```

Use this when the only change is a workflow file (otherwise `detect-changes` will skip all builds and the deploy step runs but no new image is pulled).

---

## Environments

### Local
- URL: http://127.0.0.1:9068
- DB: `geomanager` user / `geomanager_web` DB / port 5431
- Volumes: `eafw_clean_*` (override file maps them)

### Staging
- URL: http://floodwatch.icpac.net (HTTP-only for now; CSRF/SESSION_COOKIE_SECURE=False)
- Server: 41.139.151.242 (SSH alias `staging`, user `hkoros`, key `~/.ssh/eafw_staging_deploy`)
- Repo: `~/projects/flood_watch_system`
- DB: `eafw_user` / `eafw_db` / port 5441
- DNS: external `eadw-nginx` proxies to `eafw-nginx` (port 9068). **Do not modify `eadw-nginx`.**

### Production
- Same server currently. HTTPS pending.

---

## SSH Discipline (avoid zombies)

When running multiple commands on staging, **batch into ONE ssh session**:

```bash
ssh staging '
  cd ~/projects/flood_watch_system
  command 1
  command 2
  ...
'
```

Or use a heredoc inside `docker exec`:

```bash
ssh staging 'docker exec -i eafw-cms /home/app/.venv/bin/python manage.py shell' <<'PY'
# python code here
PY
```

**Do not** open one short-lived ssh per command — sshd will rate-limit and you'll see `Connection timed out`. If you must run many independent calls, use SSH multiplexing:

```bash
ssh -o ControlMaster=auto -o ControlPath=~/.ssh/cm-%r@%h:%p -o ControlPersist=5m staging 'command'
```

Before opening a new session, kill any leftover ones:

```bash
pkill -f 'ssh staging'
```

Never leave a Django shell heredoc running in the background — it holds the session open.

---

## Microservices In Detail

### `eafw_geomanager` (icpac-igad/geomanager @ eafw)
- Wagtail-based geospatial data manager
- Models: `Dataset`, `Category`, `Layer` variants (raster/vector/WMS), `Geostore`, `AdminBoundary`
- Provides `/api/datasets/`, `/api/raster-data/pixel/...`, `/api/file-raster/.../tiles/...`, `/api/admin-boundary/...`
- Translation app at `geomanager/translation/` provides `{% load geomanager_translate %}`. **Was missing for a long time** — we added it in commit `63ec3c4`. If a CMS template loads this tag and the app isn't installed, every page rendering through `base.html` (the project base, not the dashboard one) crashes.

### `eafw_geomanager_web` (icpac-igad/geomanager-web @ eafw) — the bulk of EAFW backend
- Django/Wagtail project. Installs `geomanager`, `georeport`, etc. as pip deps.
- `home/views.py` — flood APIs, the WHCA published report, the API docs page, the admin bulletin tracker, the project exit view
- `home/middleware.py` — `ProjectExitButtonMiddleware`, `ReportSectionAuthMiddleware`
- `home/templates/dashboard/published_report.html` — the WHCA published report template
- `home/templates/dashboard/whca_admin_bulletin.html` — submission tracker for regional admins
- `home/templates/home/api_docs.html` — public data API documentation
- `home/templates/partials/{navbar,footer,google_translate}.html` — site chrome
- `home/models.py` — `HomePage`, `ProjectPage` (with `scope_key`, `watermark_image`, Orderable `contacts`), `ProjectContact` (Orderable child), `Navbar` (with `help_url`), `Footer`, `LanguageSettings`, `Language`, `SiteTheme`
- `geomanagerweb/urls.py` — registers all of the above plus the upstream geomanager URLs
- `geomanagerweb/settings/base.py` — `MIDDLEWARE` includes both new middlewares
- `docker/cms/docker-entrypoint.sh` — **THIS IS THE ONE THE CMS IMAGE USES** (see Dockerfile distinction above). Wipes `STATIC_ROOT` manually before `collectstatic --no-input` to avoid the Django 4.2 `--clear` race that produced `FileNotFoundError` on `wagtailadmin/js/userbar.<hash>.js`.
- **ProjectPage editor pattern**: contacts and watermark image are now CMS-driven. Add multiple contacts via Wagtail admin → WHCA Project → Contact & Links → Additional Contacts (InlinePanel, drag-to-reorder). Upload watermark via Hero Section → Watermark Image. **Never hardcode email literals or image paths in `project_page.html`.**

### `eafw_geomapviewer` (icpac-igad/geomapviewer @ eafw)
- Next.js + MapLibre GL + Redux
- Component dirs use `index.js` re-exports for clean imports — **forgetting `index.js` breaks the webpack build** (`Module not found: Can't resolve '.../bottom-chart-panel'`). Always create:
  ```js
  // index.js
  export { default } from "./component";
  ```
- New chart components: `geoglows-chart`, `multimodel-chart`, `bottom-chart-panel`, `map-toolbar`, `highlight-marker`

---

## Modular Forecast-Chart Pipeline

**One chart component renders every forecast source.** Do not fork it per source.

```
data-table click → detection → bottomPanel dispatch → MultiModelChart(source=…) → useMultiModelForecast → /flood/<source>-forecast/<id>/
```

### Components
- `src/features/multimodal/MultiModelChart.jsx` — the unified chart. Accepts `source ∈ {"multimodal","googleflood","floodproofs"}` plus `pointId` + `thresholds`.
- `src/features/multimodal/useMultiModelForecast.js` — hook picks the backend endpoint based on `source`.
- `src/components/chart/ChartCanvas/component.jsx` — Recharts shell. Accepts `yMaxHints` so threshold lines above the data peak still render in-scale.
- `src/components/map/components/popup/components/data-table/component.jsx` — detects which layer was clicked and dispatches the bottom panel:
  - `isMultiModelLayer = /multi|mike|geosfm/i.test(layerName)` — covers Multi Model, Mike Hydro, GeoSFM (all use `multimodal_forecast` endpoint, each filters by model column).
  - Floodproofs: `layerName.includes("floodproof")` + `section_id` field.
  - Google Flood: `layerName.includes("google flood")` + `gauge_id` field.
  - GEOGloWS: dedicated `geoglows-chart` component, same bottom-panel host.
- `src/layouts/map/components/bottom-chart-panel/component.jsx` — the dispatcher. Matches `type ∈ {"multimodel","geoglows","googleflood","floodproof"}` and renders the right chart.

### Backend endpoints — identical JSON shape
All three endpoints in `eafw_geomanager_web/home/views/forecast.py` return the same shape so MultiModelChart renders any of them without a branch:

| Route | Data source |
|---|---|
| `/flood/multimodal-forecast/<point_id>/` | `gha.multimodal_forecasts` (wide: geosfm, mike_hydro_*, daily_avg) |
| `/flood/google-flood-forecast/<gauge_id>/` | `gha.google_flood_points_latest.forecasts_json` |
| `/flood/floodproofs-forecast/<section_id>/` | `gha.merged_deterministic_geojson` (parsed CSV time-series) |
| `/api/flood/geoglows-forecast/<river_id>/` | `geoglows.ecmwf.int` proxy (separate component) |

**Defensive jsonb decoding:** `psycopg2` sometimes returns `jsonb` columns as strings. Every endpoint does `if isinstance(val, str): val = json.loads(val)`. Don't remove these guards.

### Per-model vector-tile pattern
One parametrised tile function serves Multi Model, Mike Hydro, and GeoSFM:

```sql
gha.multimodal_points_by_model(z, x, y, model_key TEXT, date TEXT, scope TEXT)
-- model_key ∈ {daily_avg, geosfm, floodproof, mike_hydro_rfe, mike_hydro_chirp, mike_hydro_imerg}
```

VectorTileLayer `base_url` carries the filter as a query param:
- `…/gha.multimodal_points_by_model/{z}/{x}/{y}.pbf?model_key=mike_hydro_rfe`
- `…/gha.multimodal_points_by_model/{z}/{x}/{y}.pbf?model_key=geosfm`
- Multi Model (aggregated) keeps the older `gha.multimodal_points_alerts` (no model_key).

**Adding a new model:** add column to `gha.multimodal_forecasts`, extend the CASE branches in `gha.multimodal_points_by_model`, insert one VectorTileLayer row. No frontend change.

### Separate tile functions (DON'T merge these)
- `floodproofs.discharge_points_clustered` — SFTP-ingested, stored in `gha.merged_deterministic_geojson`. Thresholds are `Q_THR1/2/3` per feature. `floodproof` column in `multimodal_forecasts` is intentionally empty — Floodproofs has its own pipeline.
- `gha.google_flood_points_alerts` — Google API data in `gha.google_flood_points_latest`. **Classify against OUR per-gauge thresholds (`threshold_alert/alarm/emergency`), NOT Google's seasonal `latest_severity`** — Google's flag is "above normal for this time of year," which disagrees with the threshold-based chart.

### DB tile functions (db-init/)
| File | Function | Layer |
|---|---|---|
| `25-admin-tile-functions-plain.sql` | various admin functions | boundaries |
| `27-floodproofs-points-tile.sql` | `floodproofs.discharge_points_clustered` | Floodproofs |
| `28-multimodal-points-by-model.sql` | `gha.multimodal_points_by_model` | Mike / GeoSFM / Multi |
| `29-google-flood-tile.sql` | `gha.google_flood_points_alerts` | Google Flood |

After editing any of these: `docker restart eafw-tileserv` to let pg_tileserv rediscover.

---

### `eafw_georeport` (icpac-igad/georeport @ eafw)
- Reusable bulletin/assessment package
- Models: `BulletinConfig`, `AssessmentRound` (with `scope` field), `CountrySubmission`, `AdminAssessment`, `BulletinSection`, `BulletinExpertComment`
- URLs at `/reports/...`: `dashboard_view`, `bulletin_view`, `assessment_view`, `bulletin_login_view`, `assessment_save`, `assessment_choropleth_api`
- Auth: `assessment_view` reads `request.user.first_name` as the country name. `request.user.last_name` is the role label (e.g. `MET Expert` / `Hydro Expert`).

---

## WHCA Assessment Report — End-to-End

### Data model
- `AssessmentRound(scope='whca', is_active=True)` — one per active assessment cycle
- 5 expected countries: Sudan, South Sudan, Uganda, Ethiopia, Rwanda
- Per (country, admin_unit), expects **two** `CountrySubmission` rows: one MET Expert + one Hydro Expert
- Each submission has multiple `AdminAssessment` rows (one per admin unit) with `severity` (`normal`/`low`/`medium`/`high`/`very_high`), `comment`, `population_affected`

### Severity aggregation
- The published map colors each admin polygon by **max severity** across MET + Hydro (precautionary EW principle)
- Severity rank: `{normal: 0, low: 1, medium: 2, high: 3, very_high: 4}`
- The side panel still shows BOTH expert opinions individually so disagreement is visible

### Scope-driven, not hardcoded
- `home/views.py`:
  ```python
  SCOPE_ADMIN_TABLES = {
      "whca": {
          0: ("gha.whca_admin0", "country"),
          1: ("gha.whca_admin1", "name_1"),
          2: ("gha.whca_admin2", "name_2"),
      },
  }
  ```
  Add new project scopes by adding one dict entry — no view changes needed.
- `_load_scope_polygons(scope, level_country_pairs)` queries the right table based on `scope` + admin level
- `published_report_view`, `whca_admin_bulletin_view`, `project_exit_view` all read `?scope=` from the query string

### URLs
| Route | View | Who |
|---|---|---|
| `/whca-project/` | Wagtail `ProjectPage` (slug `whca-project`, `scope_key='whca'`) | Public landing page with 3 CTAs |
| `/reports/whca` (alias) → `/reports/bulletin/?scope=whca` | `assessment_entry_view` → routes by user type | All |
| `/reports/bulletin/?scope=whca` (anon) | `bulletin_view` (upstream) → login form | Anon |
| `/reports/bulletin/?scope=whca` (NMHS expert logged in) | `assessment_view` (upstream) → per-country editor | NMHS expert |
| `/reports/bulletin/?scope=whca` (superuser) | **`whca_admin_bulletin_view`** — submission status dashboard | Regional admin |
| `/reports/published/?scope=whca` | `published_report_view` — public read-only choropleth + table + exports | Anyone |
| `/reports/published/?scope=whca&format=csv` | CSV download (one row per (admin, expert)) | Anyone |
| `/reports/project-exit/?scope=whca` | `project_exit_view` — logs out + redirects to `ProjectPage.url` for that scope | Logged in or anon |
| `/reports/api/v1/assessment/choropleth/?scope=whca` | upstream georeport API | JSON: round + assessments + submitted_countries + expected_countries |

### Middleware
- **`ProjectExitButtonMiddleware`** injects an "← Exit to <Project Title>" button into the assessment editor sidebar (`.assessment-left`) on any `/reports/bulletin*` or `/reports/assessment*` page that has a `?scope=` param. The label and target URL are looked up from `home.ProjectPage` by `scope_key` — no project name hardcoded.
- **`ReportSectionAuthMiddleware`** flushes the user session whenever a logged-in user navigates **out of** `/reports/`, forcing a fresh login on next visit. Stores `_in_reports_section=True` in the session as a marker. Excluded path: `/reports/project-exit/` (so logout-then-redirect doesn't double-flush).
- Both registered in `geomanagerweb/settings/base.py` MIDDLEWARE.

### Published report features
- **One consolidated table** for all 5 countries: `Country | Admin | MET | Hydro` columns, MET/Hydro cells colored by severity, comments below
- **Cascade filtering**: click country cell → table + map filter to that country only; click admin row → filter to that single admin
- **Exports** (filter-aware — only the visible subset): CSV, PNG (composited map+title+legend), PDF (autoTable per country with severity-tinted cells)
- **Legend** overlaid top-left of the map, ordered HIGH → low → not-assessed
- **Hollow polygons** for unassessed admins in countries that have submitted
- Map uses MapLibre GL with `preserveDrawingBuffer: true` so `canvas.toDataURL()` works for PNG/PDF
- Server-side polygon load via PostGIS (no client fetches → fast first paint)
- `<h1>` is `Country Submission Status`, then `<h2>` for the table section (Wagtail accessibility checker validates heading hierarchy)

### Test users (local + staging — same passwords)
**13 accounts** seeded by `manage.py shell` script. **Credentials live in `WHCA_CREDENTIALS.md`** (gitignored, never commit).
- 3 regional admins (`rtripathi`, `hkoros`, `mzaroug`) — `is_staff=True`, `is_superuser=True`, group `WHCA Regional Admins`
- 10 NMHS country experts: `<country>_<role>` where country in `{sudan, ss, uganda, ethiopia, rwanda}` and role in `{met, hydro}`
- Username convention: experts have `first_name = country name` (e.g. `Sudan`), `last_name = role label` (e.g. `MET Expert`) — the upstream `assessment_view` reads `first_name` to scope per-country edit access. **This is fragile** — flagged for replacement with Django Groups (`Country: Sudan`, etc) post-training.

---

## Language Switcher (Google Translate)

### How it works
- DB-driven via `home.models.LanguageSettings` (singleton) + `home.models.Language` (Orderable rows)
- Adding a language = create a `Language` row in Wagtail admin (Settings → Language Settings)
- One language can be `is_default=True` — that's the SOURCE language Google Translate translates FROM
- The CMS context processor `home.context_processors.language_context` injects `language_settings`, `languages`, `default_language` into every request
- `home/templates/partials/google_translate.html` renders the JS that uses the Google Translate widget

### The cookie scoping bug (fixed in commit `44033b2`)
**Symptom:** select French → page translates → select English → page **stays in French**.

**Root cause:** Google Translate sets `googtrans=/en/fr` cookies at the **parent domain** (`.icpac.net`). The old `deleteCookie` only cleared `floodwatch.icpac.net` and `.floodwatch.icpac.net`. The parent-domain cookie survived → on reload, Google retranslated.

**Fix:** `deleteCookieAllScopes(name)` walks every parent domain (host, .host, parent.tld, .parent.tld, ...) AND three path variations (`/`, `/en`, `/en/`). `setGoogtransAll(value)` mirrors the same behavior when applying a translation. `switchLanguage` uses `defaultLangCode` (the CMS-flagged default) instead of hardcoding `'en'`. The auto-redirect-on-first-visit was removed (caused infinite reloads when default was non-English).

**Modular for any language:** add a new `Language` row in Wagtail admin → it appears in the dropdown automatically, no code changes.

---

## API Documentation

### Public docs page
- View: `home.views.api_docs_view` at `/docs/api/`
- Footer link: in TOOLS & DATA section of the Wagtail Footer model (added via DB seeding, not template)
- Static catalog of all read endpoints, organized into 8 sections (Dataset Catalog, Raster Data, Raster File Inspection, Vector Data, Admin Boundaries, Flood Forecasts, Assessment Reports, Raster WMS)
- **Excludes** auth/user/CMS endpoints (data + reports only by design)
- 71 endpoints documented

### Future
- Replace static catalog with `drf-spectacular` Swagger UI once we add it to `pyproject.toml` and rebuild the CMS image. The `api_docs_view` can then redirect to `/api/schema/swagger-ui/`. Function-based views in `home/views.py` get annotated with `@extend_schema(...)` for proper schemas.

---

## Conventions (NEVER violate without explicit user approval)

1. **No hardcoding.** URLs, country lists, thresholds, scope keys, project names — all come from DB (Wagtail StreamFields, model rows), env vars, or query params. Patterns: `SCOPE_ADMIN_TABLES` registry, `ProjectPage.scope_key` lookups, `getattr(settings, ...)`.
2. **Non-alarmist language.** "Discharge Exceedance" not "Flood Alert". Severities: `Very High / High / Medium / Low / Normal` (never `Extreme / Severe / Moderate`).
3. **Modular project scopes.** Adding a new project = add a `ProjectPage` (with `scope_key`), add admin tables to `gha.<scope>_admin0/1/2`, add one entry to `SCOPE_ADMIN_TABLES`, configure `cta_buttons` in Wagtail admin. **No code in views/middleware should mention WHCA literally** — only the registry knows.
4. **Container naming:** `eafw-*` prefix (no `clean` suffix in modern compose).
5. **Vector tile URLs:** always absolute (mapviewer web worker can't resolve relative).
6. **Microservice isolation:** keep `eafw-jobs` separate from `eafw-cms`. Never merge.
7. **DB safety on staging:** never `docker compose down`, never `docker rm -f` the DB container. Use `docker compose stop <service>` or `scripts/deploy.sh`. Volumes are pinned (`eafw_pgdata`, `eafw_media`, etc.) so deploy never recreates them.
8. **Migrations are mandatory.** If you add a model field, generate the migration **before** committing. The `home_navbar.help_url` field shipped without a migration once and broke fresh deploys until commit `44033b2` added `0027_navbar_help_url.py`.
9. **Author commits as Hillary Koros, no Claude trailer.** Per-clone may need `git config user.{name,email}` once.
10. **Local submodule trees are ahead of GitHub during active dev.** Never use a Dockerfile that `git clone`s from GitHub for a local build — it ships stale code. Always build from the LOCAL `COPY . .` context.
11. **Don't rewrite infra ("fix") without reading this file first.** Recurring footguns: compose `dockerfile:` path, the 4-stage mapviewer build, the CMS `docker-entrypoint.sh` trap (submodule vs parent). Re-deriving these from scratch each session is how we regress.

---

## Do / Don't — recurring footguns

**DO:**
- **Always run `docker compose …` from the repo ROOT** (`flood_watch_system/`), never from `eafw_geomanager_web/`. Only the root has `.env` with `COMPOSE_PROJECT_NAME=eafw`; without it, compose defaults the project name to the cwd directory (`eafw_geomanager_web`) and creates **duplicate** volumes/networks under that prefix while nginx remains bound to the `eafw_*` originals. Symptom: `/mapviewer/` returns 200 but every `/_next/static/*` 404s. Verify: `docker inspect eafw-mapviewer --format '{{range .Mounts}}{{.Name}} -> {{.Destination}}{{println}}{{end}}'` — expect `eafw_mapviewer_static`, not `eafw_geomanager_web_*`.
- Use `docker compose build geomanager_mapviewer` (no flags). Honors the stage cache; 60–90s for source-only rebuilds.
- After the build finishes, `docker rm -f eafw-mapviewer && docker compose up -d --no-deps geomanager_mapviewer` if compose complains about the existing container.
- Verify the new bundle: `docker exec eafw-mapviewer sh -c "grep -rln 'unique_string' /app/.next/static | head -3"` — 0 matches means the build didn't pick up your edit.
- After changing a `db-init/*.sql` tile function, run the SQL against the running DB (it's idempotent — `CREATE OR REPLACE`) and `docker restart eafw-tileserv`. Don't wait for a recreate-from-init-scripts cycle.
- When seeding DB rows via Django shell, read `render_layers_json` (JSONB) when `use_render_layers_json=true` — `render_layers` (StreamField) is the CMS-editor surface, and calling `save()` on a layer whose `render_layers` is a raw JSON array (not a StreamValue) fails with `KeyError: 'value'`. Workaround: reset `render_layers='[]'::jsonb` via SQL before `.save()`.
- Save new feedback memories when the user corrects or confirms an unusual approach. Future sessions lose all conversation context.

**DON'T:**
- ❌ `docker builder prune -af` to "clean up" — wipes the 4-min yarn-install cache. Only use when disk-pressure is real.
- ❌ `docker compose build --no-cache geomanager_mapviewer` unless `package.json`/`yarn.lock` actually changed.
- ❌ Change `eafw_geomanager_web/docker-compose.yml`'s `build.dockerfile:` path. It's pinned to the submodule location; CI + staging assume it.
- ❌ Replace the mapviewer Dockerfile with any variant that does `git clone git@github.com:icpac-igad/geomapviewer.git`. Local source is ahead of GitHub.
- ❌ Put native libs (`libgl1`, `libpng-dev`) only in the `deps` stage — `yarn build` runs in `builder` and needs them too.
- ❌ Re-snap the map / re-center after a chart opens — the pulse marker has to stay exactly where the user clicked. `featureLatlng` (snap-to-Point) is OK; any `setMapSettings` after click causes visible drift.
- ❌ Trust Google Flood's `latest_severity` for colour-coding. It's seasonal. Classify against OUR per-gauge thresholds instead.
- ❌ Run a staging-DB restore (`restore-staging-local.sh`) mid-session and assume local DB migrations are preserved — the script drops and reloads `cms/gha/alerts` schemas. Re-apply any local-only `db-init/*.sql` patches afterwards.
- ❌ Use `<React.Fragment>` (or any wrapper component returning an array) to group children under a Recharts `ComposedChart`. Recharts inspects **direct children only** for series/reference-lines. Use `flatMap` to emit a flat array.

---

## Troubleshooting Cheat Sheet

### `Module not found: Can't resolve '.../bottom-chart-panel'`
Webpack can't import a directory — missing `index.js`. Add `export { default } from "./component";`.

### `home_navbar.help_url does not exist`
Missing migration for the Navbar model. `manage.py makemigrations home && manage.py migrate home`. Commit the migration to upstream `geomanager-web`.

### `geomanager_translate is not a registered tag library`
The `geomanager.translation` app isn't installed in the current `geomanager` package version. Either upgrade `geomanager` or remove the `{% load geomanager_translate %}` from the partial.

### `Could not access submodule 'eafw_geomanager_web'` during deploy
The deploy server has a stale legacy `eafw_geomanager_web/` directory blocking the submodule clone. The deploy workflow's `mv ${sub} ${sub}.legacy.${TS}` step should handle this. If it doesn't, SSH in and rename manually.

### `[Errno 2] No such file or directory: '.../wagtailadmin/js/userbar.0264c262da16.js'` during collectstatic
Stale `eafw_static` volume manifest. `docker compose stop eafw-cms`, wipe the volume, restart. Container's entrypoint re-runs collectstatic.

### Browser shows old content after a deploy
Wagtailcache (memcached) is serving stale HTML. `docker exec eafw-memcached sh -c "echo flush_all | nc localhost 11211"` and restart the CMS container.
**Note**: wagtailcache ignores query strings by default, so cache-busting via `?_nl=<ts>` doesn't bypass it. Always flush memcached after content/template changes.

### Image renditions return 404 (broken images on the page)
Orphaned `wagtailimages.Rendition` rows in the DB referencing files that an earlier broken `collectstatic --clear` deleted. Wagtail trusts the DB row exists and serves the URL — but the file is gone, so nginx returns 404. **Fix**: purge orphan rows; Wagtail regenerates them lazily on the next page render:
```python
import os
from wagtail.images.models import Rendition
MEDIA_ROOT = "/home/app/media"
orphans = [r.pk for r in Rendition.objects.all().iterator()
           if not os.path.exists(os.path.join(MEDIA_ROOT, r.file.name))]
Rendition.objects.filter(pk__in=orphans).delete()
print(f"deleted {len(orphans)} orphans")
```
Then flush memcached and `curl` each affected page once to trigger regeneration.

### Mapviewer build fails on `RUN yarn build`
Likely a missing `index.js` in a new component dir, or a broken import path. Read the import trace in the build log carefully — webpack reports the actual unresolved module.

### Language switcher stays on the last language after switching back
Cookie scope bug — see the "Language Switcher" section above. Fix is in commit `44033b2` of geomanager-web.

### Force build via workflow_dispatch
Use when only the workflow file changed (otherwise `detect-changes` skips all builds):
```bash
GH_TOKEN=<token> gh workflow run "Build & Deploy to Staging" \
  --repo icpac-igad/flood_watch_system --ref eafw -f force_build=true
```

### Cancel a stuck CI run
```bash
GH_TOKEN=<token> gh run cancel <run-id> --repo icpac-igad/flood_watch_system
```

---

## After Making Changes — Always

1. **Test locally first** — `docker exec eafw-cms /home/app/.venv/bin/python manage.py shell` for DB checks, `curl http://127.0.0.1:9068/...` for endpoint checks.
2. **Commit + push to the relevant submodule's eafw branch.**
3. **Bump the parent's submodule pointer + push.**
4. **Watch CI:** `gh run list --workflow="Build & Deploy to Staging" --repo icpac-igad/flood_watch_system`
5. **If CI builds nothing** (because only workflow file changed): trigger `force_build=true`.
6. **After deploy:** flush memcached on staging if a template/content change isn't visible, then hard-refresh the browser.
7. **Verify on staging** with `curl` (not just the browser — your browser might be caching).
