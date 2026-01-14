FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    curl \
    wget \
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

# Create directories
RUN mkdir -p /app/data /app/logs /app/credentials

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/app/data
ENV LOGS_DIR=/app/logs

# Default command: run the scheduler (like Celery Beat)
CMD ["python", "-m", "pyfloodwatch.scheduler"]
