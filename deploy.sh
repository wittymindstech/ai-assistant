#!/bin/bash

# Complete AI Assistant Deployment Script
# This script deploys all components: Kafka, AI Assistant, and Angular UI

set -e

echo "🚀 AI Assistant Complete Deployment"
echo "=================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    echo "   On macOS: Open Docker Desktop"
    echo "   On Linux: sudo systemctl start docker"
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose > /dev/null 2>&1; then
    echo "❌ Docker Compose not found. Please install Docker Compose."
    exit 1
fi

echo "✅ Docker is running"

# Set environment variables
export GOOGLE_API_KEY="${GOOGLE_API_KEY:-AIzaSyDnHyzMM3HrGbbBjwnhmGD55Ye2q9RWUF0}"

echo "🔧 Building and starting all services..."

# Start all services
docker-compose -f docker-compose.full.yml up -d --build

echo ""
echo "⏳ Waiting for services to be healthy..."
echo ""

# Wait for Kafka to be ready
echo "Waiting for Kafka..."
timeout=60
counter=0
while ! docker-compose -f docker-compose.full.yml exec -T kafka kafka-broker-api-versions.sh --bootstrap-server kafka:29092 > /dev/null 2>&1; do
    if [ $counter -ge $timeout ]; then
        echo "❌ Kafka failed to start within ${timeout} seconds"
        exit 1
    fi
    counter=$((counter + 1))
    echo -n "."
    sleep 1
done
echo " ✅ Kafka ready"

# Wait for AI Assistant to be ready
echo "Waiting for AI Assistant..."
counter=0
while ! curl -f http://localhost:8001/queue > /dev/null 2>&1; do
    if [ $counter -ge 30 ]; then
        echo "❌ AI Assistant failed to start within 30 seconds"
        exit 1
    fi
    counter=$((counter + 1))
    echo -n "."
    sleep 1
done
echo " ✅ AI Assistant ready"

# Wait for Frontend to be ready
echo "Waiting for Frontend..."
counter=0
while ! curl -f http://localhost:4200 > /dev/null 2>&1; do
    if [ $counter -ge 30 ]; then
        echo "❌ Frontend failed to start within 30 seconds"
        exit 1
    fi
    counter=$((counter + 1))
    echo -n "."
    sleep 1
done
echo " ✅ Frontend ready"

echo ""
echo "🎉 All services deployed successfully!"
echo ""
echo "📊 Service URLs:"
echo "  🔗 Kafka UI:           http://localhost:8080"
echo "  🤖 AI Assistant API:    http://localhost:8001"
echo "  📱 API Docs:           http://localhost:8001/docs"
echo "  🎯 Queue Status:       http://localhost:8001/queue"
echo "  🛍️  Ecommerce Frontend: http://localhost:4200"
echo ""
echo "🧪 Test the deployment:"
echo "  curl -X POST http://localhost:8001/enqueue \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"query\":\"Hello AI Assistant!\"}'"
echo ""
echo "🛑 To stop all services:"
echo "  docker-compose -f docker-compose.full.yml down"
echo ""
echo "📝 View logs:"
echo "  docker-compose -f docker-compose.full.yml logs -f ai-assistant"