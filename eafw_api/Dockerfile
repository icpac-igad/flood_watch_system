# EAFW API - FloodWatch FastAPI Service
# Author: Hillary Koros, ICPAC

FROM python:3.12-slim

LABEL maintainer="Hillary Koros <hkoros@icpac.net>"
LABEL description="East Africa Flood Watch - FastAPI Service"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and readme first for better caching
COPY pyproject.toml README.md ./

# Copy application code
COPY src/ ./src/

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install .

# Create non-root user
RUN useradd --create-home --shell /bin/bash eafw && \
    chown -R eafw:eafw /app
USER eafw

# Expose port
EXPOSE 9060

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9060/health || exit 1

# Run the application
CMD ["uvicorn", "eafw_api.app:app", "--host", "0.0.0.0", "--port", "9060"]
