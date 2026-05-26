#!/bin/bash

# Run AI assistant with Kafka integration
# Assumes Docker Compose Kafka stack is already running

set -e

if [ -z "${GOOGLE_API_KEY:-}" ]; then
  echo "❌ GOOGLE_API_KEY is required to run with Kafka. Set it before running this script."
  exit 1
fi

export ENVIRONMENT="production"
export KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
export KAFKA_TASK_TOPIC="assistant_tasks"
export KAFKA_RESPONSE_TOPIC="assistant_responses"
export KAFKA_CONSUMER_GROUP="assistant_agent_group"

echo "🚀 Starting AI Assistant with Kafka integration..."
echo ""
echo "Configuration:"
echo "  KAFKA_BOOTSTRAP_SERVERS=$KAFKA_BOOTSTRAP_SERVERS"
echo "  KAFKA_TASK_TOPIC=$KAFKA_TASK_TOPIC"
echo "  KAFKA_RESPONSE_TOPIC=$KAFKA_RESPONSE_TOPIC"
echo "  KAFKA_CONSUMER_GROUP=$KAFKA_CONSUMER_GROUP"
echo ""
echo "📊 Kafka UI: http://localhost:8080"
echo "🔌 API Server: http://127.0.0.1:8001"
echo ""

source .venv/bin/activate
python3 -m uvicorn main:app --host 127.0.0.1 --port 8001 --reload
