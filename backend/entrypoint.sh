#!/bin/bash
set -e

echo "🚀 Starting FloodWatch Backend Initialization..."

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL..."
while ! nc -z ${DB_HOST} ${DB_PORT}; do
  sleep 1
done
echo "✅ PostgreSQL is ready!"

# Run migrations
echo "🔄 Running Django migrations..."
python manage.py migrate --noinput

# Initialize PostGIS extensions
echo "🗺️ Initializing PostGIS..."
python manage.py init_postgis || echo "⚠️ PostGIS initialization warning (may already exist)"

# Create superuser if it doesn't exist
echo "👤 Creating superuser if needed..."
python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@floodwatch.com', 'admin123')
    print('✅ Superuser created')
else:
    print('ℹ️ Superuser already exists')
END

# Collect static files
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

# Test database connection
echo "🔍 Testing database connection..."
python manage.py test_db_connection || echo "⚠️ Database connection test failed"

echo "✅ Backend initialization complete!"

# Start the server
exec "$@"