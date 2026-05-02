#!/bin/bash

# Start Kafka locally using Docker Compose
# This brings up Zookeeper, Kafka, and Kafka UI

set -e

echo "Starting Kafka infrastructure..."
docker-compose up -d

echo ""
echo "✅ Kafka services started!"
echo ""
echo "📊 Kafka UI available at: http://localhost:8080"
echo ""
echo "🚀 To run the AI assistant with Kafka integration:"
echo ""
echo "  export KAFKA_BOOTSTRAP_SERVERS='localhost:9092'"
echo "  export KAFKA_TASK_TOPIC='assistant_tasks'"
echo "  export KAFKA_RESPONSE_TOPIC='assistant_responses'"
echo "  export KAFKA_CONSUMER_GROUP='assistant_agent_group'"
echo "  source .venv/bin/activate"
echo "  python3 -m uvicorn main:app --host 127.0.0.1 --port 8001"
echo ""
echo "Or use: source scripts/run_with_kafka.sh"
echo ""
