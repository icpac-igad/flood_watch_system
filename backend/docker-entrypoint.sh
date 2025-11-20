#!/bin/bash
set -e

# Wait for postgres to be ready
echo "Waiting for PostgreSQL..."
while ! nc -z ${DB_HOST:-postgis} ${DB_PORT:-5432}; do
  sleep 0.1
done
echo "PostgreSQL started"

# Wait for Redis to be ready (for Celery)
echo "Waiting for Redis..."
while ! nc -z ${REDIS_HOST:-redis} ${REDIS_PORT:-6379}; do
  sleep 0.1
done
echo "Redis started"

# Determine service type from SERVICE_TYPE environment variable or container hostname
SERVICE_TYPE=${SERVICE_TYPE:-backend}

case "$SERVICE_TYPE" in
  backend)
    # Run migrations
    echo "Running migrations..."
    python manage.py migrate --noinput

    # Collect static files
    echo "Collecting static files..."
    python manage.py collectstatic --noinput

    # Start Gunicorn
    echo "Starting Gunicorn..."
    exec gunicorn flood_watch_system.wsgi:application --bind 0.0.0.0:8090 --workers 4 --timeout 120
    ;;

  celery)
    # Start Celery Worker
    echo "Starting Celery Worker..."
    exec celery -A flood_watch_system worker --loglevel=info
    ;;

  celery-beat)
    # Start Celery Beat
    echo "Starting Celery Beat..."
    exec celery -A flood_watch_system beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    ;;

  *)
    echo "Unknown SERVICE_TYPE: $SERVICE_TYPE"
    exit 1
    ;;
esac
