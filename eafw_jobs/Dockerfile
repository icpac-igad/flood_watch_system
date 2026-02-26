FROM python:3.10-slim

# Set working directory
WORKDIR /floodwatch_jobs/app

# Install system dependencies (includes GDAL libs for rasterio/COG export)
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    curl \
    gdal-bin \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install --no-cache-dir poetry==1.7.1

# Copy poetry files
COPY pyproject.toml ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Copy application code
COPY pyfloodwatch/ ./pyfloodwatch/
COPY config/ ./config/

# Create data, logs, and COG output directories
RUN mkdir -p /floodwatch_jobs/app/data /floodwatch_jobs/app/logs /data/cogs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV APP_DIR=/floodwatch_jobs/app

CMD ["python", "-m", "pyfloodwatch.download"]
