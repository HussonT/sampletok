#!/bin/bash

echo "🚀 Starting SampleTok Backend (Simplified with Inngest)"
echo "=================================================="

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    echo "🐍 Activating virtual environment..."
    source venv/bin/activate
fi

# Copy .env.example to .env if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "⚠️  Please update .env with your configuration if needed"
fi

# Start Docker services (PostgreSQL and MinIO)
echo "🐳 Starting Docker services..."
docker-compose up -d

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL..."
sleep 5
until docker-compose exec -T postgres pg_isready -U sampletok > /dev/null 2>&1; do
    echo "   Still waiting for PostgreSQL..."
    sleep 2
done
echo "✅ PostgreSQL is ready!"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
# Skip numpy as it requires special handling for Python 3.13
grep -v "numpy==" requirements.txt | pip install -r /dev/stdin
# Ensure numpy is installed with a compatible version
pip list | grep -q numpy || pip install numpy

# Run database migrations
echo "🗄️ Running database migrations..."
alembic upgrade head

# Start Inngest Dev Server in background (for local development)
echo "🎯 Starting Inngest Dev Server..."
npx inngest-cli@latest dev -u http://localhost:8000/api/inngest &
INNGEST_PID=$!

# Give Inngest Dev Server time to start
sleep 3

# Start FastAPI server
echo ""
echo "✨ Everything is ready!"
echo "=================================================="
echo "📍 FastAPI:       http://localhost:8000"
echo "📚 API Docs:      http://localhost:8000/api/v1/docs"
echo "🎯 Inngest UI:    http://localhost:8288"
echo "💾 MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"
echo "=================================================="
echo ""

# Start the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Cleanup on exit
trap "kill $INNGEST_PID 2>/dev/null; docker-compose down" EXIT