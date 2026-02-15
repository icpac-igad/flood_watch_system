# Quick Start

## Prerequisites

- Docker Engine + Docker Compose plugin (`docker compose`)
- At least 8 GB RAM (16 GB recommended)
- 20+ GB free disk

## 1. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

- `CMS_DB_PASSWORD`
- `SECRET_KEY`
- `FLOODPROOFS_SFTP_*` credentials
- `ENSEMBLE_FTP_*` credentials
- `WRF_FTP_*` credentials

If using Drive sync:

- Place Google service account credentials at `eafw_jobs/credentials/google-credentials.json`
- Set `DRIVE_FOLDER_ID`

## 2. Start Services

```bash
docker compose up --build -d
```

## 3. Verify

```bash
docker compose ps
curl -f http://127.0.0.1:9068/health
curl -f http://127.0.0.1:9069/health
```

## Common Operations

### Logs

```bash
docker compose logs -f
docker compose logs -f eafw_cms
docker compose logs -f eafw_api
docker compose logs -f eafw_jobs
```

### Stop / Restart

```bash
docker compose down
docker compose restart eafw_cms eafw_api eafw_jobs
```

### Django Admin and Migrations

```bash
docker compose exec eafw_cms python manage.py migrate
docker compose exec eafw_cms python manage.py createsuperuser
```

### Run Jobs Manually

```bash
docker compose exec eafw_jobs python -m pyfloodwatch.floodproofs_sync
docker compose exec eafw_jobs python -m pyfloodwatch.ensemble_sync
docker compose exec eafw_jobs python -m pyfloodwatch.wrf_rainfall_job
```

### Database Backup / Restore

```bash
# Backup
./scripts/db-dump.sh local

# Restore
./scripts/db-load.sh backups/<dump-file>.dump
```

## Troubleshooting

### CMS Login Loop on Staging

```bash
bash scripts/fix-staging-cms-login.sh
```

### Jobs Failing Due to Credentials

- Confirm `.env` has valid `FLOODPROOFS_SFTP_*`, `ENSEMBLE_FTP_*`, and `WRF_FTP_*`
- If `SYNC_SOURCE=drive`, verify `DRIVE_FOLDER_ID` and credential file path

### API Reachable Directly But Not Through Nginx

```bash
docker compose logs -f eafw_nginx eafw_api
```
