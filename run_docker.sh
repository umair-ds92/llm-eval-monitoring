#!/bin/bash
# Docker demo script

set -e

echo "🐳 LLM Eval & Monitoring Demo (Docker)"
echo "========================================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose not found. Please install it first."
    exit 1
fi

# Cleanup function
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    docker-compose down
    exit 0
}

trap cleanup EXIT INT TERM

# Build images
echo "🔨 Building Docker images..."
docker-compose build --no-cache
echo ""

# Start services
echo "🚀 Starting services..."
docker-compose up -d
echo ""

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check health
echo "🔍 Checking service health..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ API is healthy"
else
    echo "⚠️  API health check failed"
fi

if curl -s http://localhost:8501/_stcore/health > /dev/null 2>&1; then
    echo "✓ Dashboard is healthy"
else
    echo "⚠️  Dashboard health check failed"
fi

echo ""
echo "================================"
echo "🎉 All services are running!"
echo "================================"
echo "Access points:"
echo "  API:       http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo "  Dashboard: http://localhost:8501"
echo "  Database:  localhost:5432"
echo "  Redis:     localhost:6379"
echo ""
echo "View logs: docker-compose logs -f"
echo "Stop:      docker-compose down"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Follow logs
docker-compose logs -f

# Cleanup happens on Ctrl+C via trap