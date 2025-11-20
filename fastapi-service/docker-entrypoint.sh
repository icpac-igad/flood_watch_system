#!/bin/bash
set -e

# Wait for postgres to be ready
echo "Waiting for PostgreSQL..."
while ! nc -z ${DB_HOST:-postgis} ${DB_PORT:-5432}; do
  sleep 0.1
done
echo "PostgreSQL started"

# Start FastAPI with Uvicorn
echo "Starting FastAPI with Uvicorn..."
exec uvicorn main:app \
  --host 0.0.0.0 \
  --port 8001 \
  --log-level info \
  --workers 4 \
  --timeout-keep-alive 30
