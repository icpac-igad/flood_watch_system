FROM python:3.10-slim

WORKDIR /opt/eafw_jobs

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    curl \
    lftp \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install --no-cache-dir poetry==1.7.1

# Copy poetry files from eafw_jobs folder
COPY eafw_jobs/pyproject.toml ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root || true

# Copy application code from eafw_jobs folder
COPY eafw_jobs/pyfloodwatch/ ./pyfloodwatch/

# Create directories
RUN mkdir -p /opt/data /opt/logs /opt/credentials ./config

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "pyfloodwatch.scheduler"]
