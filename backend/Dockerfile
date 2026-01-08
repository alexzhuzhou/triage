FROM python:3.11-slim

# Install system dependencies including poppler-utils for PDF processing
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Cloud Run uses PORT environment variable
ENV PORT=8000
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run database migrations and start uvicorn
CMD alembic upgrade head && \
    uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
