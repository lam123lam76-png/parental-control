FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for PostgreSQL and building packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY backend_api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir psycopg2-binary uvicorn gunicorn

# Copy backend application source
COPY backend_api /app/backend_api

# Create storage directory for uploaded screenshots
RUN mkdir -p /app/backend_api/storage/screenshots

EXPOSE 8000

ENV PYTHONPATH=/app

CMD ["uvicorn", "backend_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
