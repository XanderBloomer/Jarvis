FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy application code first (needed for editable install with src layout)
COPY . .

# Install the package with dev dependencies
RUN pip install --no-cache-dir -e ".[dev]"

EXPOSE 8000

CMD ["uvicorn", "content_engine.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
