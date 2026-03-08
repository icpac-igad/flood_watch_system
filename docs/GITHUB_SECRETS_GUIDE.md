# FloodWatch — GitHub Secrets Reference

## Overview

All secrets for the FloodWatch staging/production deployment are managed in GitHub.
There are two scopes:

- **Repository secrets** — available to all workflows (CI, all environments)
- **Environment secrets** (`staging`, `production`) — scoped to deploy jobs only

> **Rule**: Real credentials go in **environment secrets**. Shared tokens (GHCR, DockerHub) go in **repository secrets**.

---

## 1. Repository-Level Secrets

These are shared across all workflows (CI + deploy).

| Secret Name | Purpose | Status | Required |
|---|---|---|---|
| `GH_PAT` | GitHub PAT for cloning private repo on staging server + GHCR login | SET | Yes |
| `GHCR_PAT` | GitHub Container Registry PAT (image push from CI) | SET | Yes |
| `GHCR_USER` | GHCR username for image push | SET | Yes |
| `DOCKERHUB_USERNAME` | DockerHub login (legacy, can remove if not used) | SET | No |
| `DOCKERHUB_TOKEN` | DockerHub token (legacy) | SET | No |

---

## 2. Staging Environment Secrets

These are used by `deploy-staging.yml` and scoped to the `staging` environment.

### Infrastructure / SSH

| Secret Name | .env Key | Purpose | Status |
|---|---|---|---|
| `DEPLOY_HOST` | — | Staging server IP (41.139.151.242) | SET |
| `DEPLOY_USER` | — | SSH user for deploy | SET |
| `SSH_KEY` | — | SSH private key for deploy | SET |

### Database

| Secret Name | .env Key | Purpose | Status |
|---|---|---|---|
| `DB_PASSWORD` | `CMS_DB_PASSWORD` | PostgreSQL password | SET |
| `DB_USER` | `CMS_DB_USER` | PostgreSQL user (eafw_user) | SET |
| `DJANGO_SECRET_KEY` | `SECRET_KEY` | Django cryptographic key | SET |

### FloodProofs SFTP (Forecast Ingestion)

| Secret Name | .env Key | Purpose | Status |
|---|---|---|---|
| `FLOODPROOFS_SFTP_HOST` | `FLOODPROOFS_SFTP_HOST` | SFTP server hostname | SET |
| `FLOODPROOFS_SFTP_PORT` | `FLOODPROOFS_SFTP_PORT` | SFTP port (default 22) | SET |
| `FLOODPROOFS_SFTP_USER` | `FLOODPROOFS_SFTP_USER` | SFTP username | SET |
| `FLOODPROOFS_SFTP_PASSWORD` | `FLOODPROOFS_SFTP_PASSWORD` | SFTP password | SET |

### Legacy SFTP (used by CMS sync)

| Secret Name | .env Key | Purpose | Status |
|---|---|---|---|
| `SFTP_HOST` | `SFTP_HOST` | SFTP host for CMS data sync | SET |
| `SFTP_PORT` | `SFTP_PORT` | SFTP port | SET |
| `SFTP_USERNAME` | `SFTP_USERNAME` | SFTP username | SET |
| `SFTP_PASSWORD` | `SFTP_PASSWORD` | SFTP password | SET |

### Ensemble FTP (Ensemble Forecast Ingestion)

| Secret Name | .env Key | Purpose | Status |
|---|---|---|---|
| `ENSEMBLE_FTP_HOST` | `ENSEMBLE_FTP_HOST` | FTP server for ensemble data | SET |
| `ENSEMBLE_FTP_PORT` | `ENSEMBLE_FTP_PORT` | FTP port (default 21) | SET |
| `ENSEMBLE_FTP_USER` | `ENSEMBLE_FTP_USER` | FTP username | SET |
| `ENSEMBLE_FTP_PASSWORD` | `ENSEMBLE_FTP_PASSWORD` | FTP password | SET |

### WRF Rainfall FTP

| Secret Name | .env Key | Purpose | Status |
|---|---|---|---|
| `WRF_FTP_HOST` | `WRF_FTP_HOST` | WRF FTP server | SET |
| `WRF_FTP_PORT` | `WRF_FTP_PORT` | WRF FTP port (default 21) | SET |
| `WRF_FTP_USER` | `WRF_FTP_USER` | WRF FTP username | SET |
| `WRF_FTP_PASSWORD` | `WRF_FTP_PASSWORD` | WRF FTP password | SET |

### Google / External APIs

| Secret Name | .env Key | Purpose | Status |
|---|---|---|---|
| `FLOODS_API_KEY` | `FLOODS_API_KEY` | Google Flood API key | SET |
| `DRIVE_FOLDER_ID` | `DRIVE_FOLDER_ID` | Google Drive folder for sync | SET |
| `GOOGLE_SEARCH_API_KEY` | `GOOGLE_SEARCH_API_KEY` | Google Custom Search API key | SET |
| `RECAPTCHA_PUBLIC_KEY` | `RECAPTCHA_PUBLIC_KEY` | reCAPTCHA site key | SET |
| `RECAPTCHA_PRIVATE_KEY` | `RECAPTCHA_PRIVATE_KEY` | reCAPTCHA secret key | SET |

### Email (SMTP)

| Secret Name | .env Key | Purpose | Status |
|---|---|---|---|
| `SMTP_EMAIL_HOST` | `SMTP_EMAIL_HOST` | SMTP server hostname | SET |
| `SMTP_EMAIL_PORT` | `SMTP_EMAIL_PORT` | SMTP port | SET |
| `SMTP_EMAIL_HOST_USER` | `SMTP_EMAIL_HOST_USER` | SMTP username | SET |
| `SMTP_EMAIL_HOST_PASSWORD` | `SMTP_EMAIL_HOST_PASSWORD` | SMTP password | SET |

---

## 3. MISSING — Secrets in .env But NOT in GitHub

These are in your local `.env` but the deploy workflow does NOT inject them. Either add them to GH secrets + deploy script, or confirm they use safe defaults.

### Needs Action

| .env Key | What It Is | Action Needed |
|---|---|---|
| `STAC_API_KEY` | Write-protect key for STAC API (nginx enforced) | **ADD to GH secrets** — required for STAC write protection |
| `ANALYTICS_PROPERTY_ID` | Google Analytics tracking ID | Exists as `STAGING_ANALYTICS_PROPERTY_ID` (repo-level) — used at build time, OK |
| `BITLY_TOKEN` | URL shortener for share links | **ADD if used** — low priority |
| `GOOGLE_CUSTOM_SEARCH_CX` | Google Custom Search engine ID | **ADD if used** — low priority |
| `GOOGLE_CREDENTIALS_FILE` | Service account JSON for Drive sync | **Not a secret** — file mounted from `eafw_jobs/credentials/` on staging server |

### Safe — Use Defaults (No Secret Needed)

| .env Key | Default Value | Why No Secret |
|---|---|---|
| `CMS_DB_USER` | `eafw_user` | Hardcoded in deploy script via `upsert_env` |
| `CMS_DB_NAME` | `eafw_db` | Hardcoded in deploy script |
| `CMS_DEBUG` | `False` | Forced to False in deploy script |
| `ALLOWED_HOSTS` | staging IPs | Hardcoded in deploy script |
| `CSRF_TRUSTED_ORIGINS` | staging URLs | Hardcoded in deploy script |
| `CORS_ALLOWED_ORIGINS` | staging URLs | Hardcoded in deploy script |
| All `*_CNTR_NAME` | Container names | Not sensitive |
| All `*_HOST_PORT` | Port numbers | Not sensitive |
| All `*_VERSION` | Image versions | Not sensitive |
| `SYNC_SOURCE`, `SYNC_INTERVAL`, `SYNC_DAYS` | Config values | Not sensitive |
| `GOOGLE_FLOOD_*` (non-key) | Chunk sizes, timeouts | Not sensitive |
| `STAC_FASTAPI_*`, `TITILER_*` | Service config | Not sensitive |

---

## 4. Deploy Workflow Secret Mapping

How `deploy-staging.yml` maps GH secrets → `.env` on staging:

```
GH Secret Name          →  .env Key
─────────────────────────────────────────────
DB_PASSWORD             →  CMS_DB_PASSWORD
DJANGO_SECRET_KEY       →  SECRET_KEY
SFTP_HOST               →  SFTP_HOST
SFTP_USERNAME           →  SFTP_USERNAME
SFTP_PASSWORD           →  SFTP_PASSWORD
FLOODPROOFS_SFTP_HOST   →  FLOODPROOFS_SFTP_HOST
FLOODPROOFS_SFTP_USER   →  FLOODPROOFS_SFTP_USER
FLOODPROOFS_SFTP_PASSWORD → FLOODPROOFS_SFTP_PASSWORD
ENSEMBLE_FTP_HOST       →  ENSEMBLE_FTP_HOST
ENSEMBLE_FTP_USER       →  ENSEMBLE_FTP_USER
ENSEMBLE_FTP_PASSWORD   →  ENSEMBLE_FTP_PASSWORD
WRF_FTP_HOST            →  WRF_FTP_HOST
WRF_FTP_USER            →  WRF_FTP_USER
WRF_FTP_PASSWORD        →  WRF_FTP_PASSWORD
FLOODS_API_KEY          →  FLOODS_API_KEY
SMTP_EMAIL_HOST         →  SMTP_EMAIL_HOST
SMTP_EMAIL_HOST_USER    →  SMTP_EMAIL_HOST_USER
SMTP_EMAIL_HOST_PASSWORD → SMTP_EMAIL_HOST_PASSWORD
```

### Not Yet Wired (need to add to deploy script)

```
STAC_API_KEY            →  STAC_API_KEY         (STAC write protection)
DRIVE_FOLDER_ID         →  DRIVE_FOLDER_ID      (Google Drive sync)
RECAPTCHA_PUBLIC_KEY    →  RECAPTCHA_PUBLIC_KEY  (optional)
RECAPTCHA_PRIVATE_KEY   →  RECAPTCHA_PRIVATE_KEY (optional)
GOOGLE_SEARCH_API_KEY   →  GOOGLE_SEARCH_API_KEY (optional)
SMTP_EMAIL_PORT         →  SMTP_EMAIL_PORT       (optional)
```

---

## 5. How to Add a New Secret

### Via CLI
```bash
# Repository secret (all workflows)
gh secret set SECRET_NAME --repo icpac-igad/flood_watch_system

# Environment secret (staging only)
gh secret set SECRET_NAME --repo icpac-igad/flood_watch_system --env staging
```

### Via GitHub UI
1. Go to repo → Settings → Secrets and variables → Actions
2. For environment secrets: Settings → Environments → staging → Add secret

### Wire it in deploy script
Add this line in `deploy-staging.yml` under the `upsert_env` section:
```bash
upsert_env "ENV_KEY_NAME" "${SECRET_NAME}"
```

And add the secret name to the `envs:` list in the SSH action.

---

## 6. Secret Rotation Checklist

| Secret | Rotation Frequency | How to Rotate |
|---|---|---|
| `DB_PASSWORD` | Quarterly | Update GH secret → redeploy → update PG password in container |
| `DJANGO_SECRET_KEY` | Annually | Update GH secret → redeploy (invalidates sessions) |
| `SSH_KEY` | Annually | Generate new keypair → update server `authorized_keys` + GH secret |
| `GH_PAT` | Per expiry | Create new PAT → update repo secret |
| `FLOODS_API_KEY` | Per Google policy | Regenerate in Google Cloud Console → update GH secret |
| `*_SFTP_PASSWORD` | Per provider policy | Coordinate with data provider → update GH secret |
| `*_FTP_PASSWORD` | Per provider policy | Coordinate with data provider → update GH secret |
| `STAC_API_KEY` | Quarterly | Generate new random key → update GH secret + nginx config |
