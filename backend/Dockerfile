# Use Python 3.11 slim image as base
FROM python:3.11-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    DJANGO_SETTINGS_MODULE=flood_watch_system.settings

# Install system dependencies including GDAL, PostGIS, and PROJ
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build essentials
    gcc g++ make \
    # PostgreSQL client and development files
    libpq-dev postgresql-client \
    # GDAL/GEOS/PROJ dependencies
    gdal-bin libgdal-dev \
    geos-bin libgeos-dev \
    proj-bin libproj-dev \
    # Additional geo libraries
    libspatialindex-dev \
    # Network utilities
    curl wget netcat-openbsd \
    # Image processing
    libjpeg-dev zlib1g-dev \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

# Set GDAL environment variables
ENV GDAL_CONFIG=/usr/bin/gdal-config \
    GEOS_CONFIG=/usr/bin/geos-config \
    PROJ_LIB=/usr/share/proj \
    GDAL_DATA=/usr/share/gdal \
    GDAL_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgdal.so

# Set the working directory
WORKDIR /app

# Upgrade pip and install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . /app/

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Create directories and set permissions
RUN mkdir -p /app/data \
             /app/staticfiles \
             /app/media && \
    chmod -R 755 /app/data

# Expose port
EXPOSE 8090

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]