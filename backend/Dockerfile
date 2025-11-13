FROM python:3.13-slim

# Install system dependencies including build tools for compiling packages
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libpq-dev \
    curl \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (essentia has prebuilt manylinux wheels)
COPY requirements.txt .
# Install build dependencies first (madmom requires Cython and numpy at build time)
RUN pip install --no-cache-dir setuptools wheel Cython==3.1.4 numpy==2.2.6
# Install madmom separately with --no-build-isolation to use the Cython we just installed
RUN pip install --no-cache-dir --no-build-isolation madmom==0.16.1
# Install remaining dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create startup script that runs migrations then starts server
RUN echo '#!/bin/bash\n\
set -e\n\
echo "Running database migrations..."\n\
alembic upgrade head\n\
echo "Starting application..."\n\
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}' > /app/start.sh && \
chmod +x /app/start.sh

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

CMD ["/app/start.sh"]
