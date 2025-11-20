#!/bin/bash
set -e

# Wait for postgres to be ready
echo "Waiting for PostgreSQL..."
while ! nc -z ${POSTGRES_HOST:-postgis} ${POSTGRES_PORT:-5432}; do
  sleep 0.1
done
echo "PostgreSQL started"

# Start TiPg with Uvicorn
echo "Starting TiPg with Uvicorn..."
exec uvicorn main:app \
  --host 0.0.0.0 \
  --port 80 \
  --log-level info \
  --workers 4 \
  --timeout-keep-alive 30
