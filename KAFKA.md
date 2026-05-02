# Kafka Integration Guide

This guide explains how to use Kafka with the AI Assistant for distributed task processing.

## Overview

Kafka integration enables:
- **Distributed Processing**: Process tasks across multiple instances
- **Asynchronous Queuing**: Submit tasks and check status later
- **Message Persistence**: Tasks are persisted in Kafka topics
- **Monitoring**: Track task flow and consumer lag in Kafka UI

## Architecture

```
┌─────────────────┐
│  Client/API     │
└────────┬────────┘
         │ POST /enqueue
         ▼
┌─────────────────────────────────────────┐
│  FastAPI Server (main.py)               │
│  - PromptQueueManager                   │
│  - Kafka Producer                       │
└─────────┬───────────────────┬───────────┘
          │                   │
          │ Publish           │ Consume
          ▼                   ▼
    ┌──────────────┐    ┌──────────────┐
    │ assistant_   │    │ Kafka        │
    │ tasks topic  │    │ Consumer     │
    └──────────────┘    └──────┬───────┘
                                │
                                ▼
                        ┌──────────────────┐
                        │ Process Task     │
                        │ query_agent()    │
                        └────────┬─────────┘
                                │
                                ▼
                        ┌──────────────────┐
                        │ Publish Response │
                        │ to response topic│
                        └──────────────────┘
```

## Quick Start

### 1. Start Kafka with Docker Compose

```bash
# Start just infrastructure (development)
docker-compose up -d

# Or start everything including the app
docker-compose -f docker-compose.full.yml up -d
```

### 2. Set Environment Variables

```bash
export KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
export KAFKA_TASK_TOPIC="assistant_tasks"
export KAFKA_RESPONSE_TOPIC="assistant_responses"
export KAFKA_CONSUMER_GROUP="assistant_agent_group"
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the App with Kafka

**Option A: Using the convenience script**
```bash
bash scripts/run_with_kafka.sh
```

**Option B: Manual setup**
```bash
source .venv/bin/activate
python3 -m uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

### 5. Submit Tasks

```bash
curl -X POST http://127.0.0.1:8001/enqueue \
  -H "Content-Type: application/json" \
  -d '{"query":"find technical skills in resume","assistant_id":"user1"}'
```

Get the response:
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "assistant_id": "user1",
  "session_id": "default"
}
```

### 6. Monitor in Kafka UI

Visit `http://localhost:8080`:
- View `assistant_tasks` topic for queued prompts
- View `assistant_responses` topic for completed results
- Check consumer group lag and status

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `KAFKA_BOOTSTRAP_SERVERS` | (none) | Kafka broker address (enables Kafka if set) |
| `KAFKA_TASK_TOPIC` | `assistant_tasks` | Topic for incoming tasks |
| `KAFKA_RESPONSE_TOPIC` | `assistant_responses` | Topic for task responses |
| `KAFKA_CONSUMER_GROUP` | `assistant_agent_group` | Consumer group ID |

### Fallback Behavior

If `KAFKA_BOOTSTRAP_SERVERS` is **not** set:
- The app uses the in-memory queue
- No Kafka integration
- Tasks are processed synchronously or queued in memory

If `KAFKA_BOOTSTRAP_SERVERS` **is** set:
- Tasks are published to Kafka
- A Kafka consumer processes tasks
- Responses are published to the response topic

## Message Schemas

### Task Message (assistant_tasks topic)

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "prompt": "find technical skills in resume",
  "assistant_id": "user1",
  "session_id": "default"
}
```

### Response Message (assistant_responses topic)

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "assistant_id": "user1",
  "session_id": "default",
  "result": {
    "response": "The resume shows proficiency in Python, Kubernetes...",
    "usage": {
      "prompt_tokens": 1234,
      "response_tokens": 567,
      "total_tokens": 1801,
      "remaining_tokens": 126199,
      "model_token_limit": 128000
    }
  },
  "error": null,
  "metadata": {
    "assistant_id": "user1",
    "session_id": "default"
  }
}
```

## Scaling

### Multiple Consumer Instances

Start multiple instances with the same `KAFKA_CONSUMER_GROUP`:

```bash
# Terminal 1
KAFKA_CONSUMER_GROUP=assistant_agent_group python3 -m uvicorn main:app --port 8001

# Terminal 2
KAFKA_CONSUMER_GROUP=assistant_agent_group python3 -m uvicorn main:app --port 8002

# Terminal 3
KAFKA_CONSUMER_GROUP=assistant_agent_group python3 -m uvicorn main:app --port 8003
```

Kafka automatically distributes tasks across consumer instances.

## Troubleshooting

### Issue: "No brokers available"
**Solution**: Ensure Kafka is running and `KAFKA_BOOTSTRAP_SERVERS` points to the correct address
```bash
docker-compose logs kafka
```

### Issue: "Topic does not exist"
**Solution**: Kafka auto-creates topics. Ensure `KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"` in Docker Compose
```bash
# Manually create topics
docker-compose exec kafka kafka-topics.sh --bootstrap-server kafka:29092 --create --topic assistant_tasks --partitions 1 --replication-factor 1
```

### Issue: Tasks not being processed
**Solution**: Check consumer lag and offset status in Kafka UI or verify the consumer is running
```bash
docker-compose logs ai-assistant
```

### Issue: Connection timeout on localhost:9092
**Solution**: When connecting from outside Docker, use `localhost:9092`. When connecting from inside Docker, use `kafka:29092`

## Performance Tuning

### Partition Count
For higher throughput, increase partitions:
```bash
docker-compose exec kafka kafka-topics.sh --bootstrap-server kafka:29092 \
  --topic assistant_tasks --alter --partitions 3
```

### Replication Factor
For production, set replication factor > 1 in docker-compose.yml:
```yaml
KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 3
```

## Monitoring & Observability

### Kafka UI Features
- **Topics**: View all topics, partitions, and replication
- **Messages**: Browse message content in topics
- **Consumers**: Monitor consumer groups and lag
- **Brokers**: Check broker health and configuration

### Key Metrics
- **Consumer Lag**: How many messages are unprocessed
- **Throughput**: Messages/second being processed
- **Latency**: Time from task submission to completion

## Production Deployment

### Docker Compose for Production

```yaml
services:
  kafka:
    environment:
      KAFKA_MIN_INSYNC_REPLICAS: 2
      KAFKA_LOG_RETENTION_HOURS: 168
      KAFKA_LOG_CLEANUP_POLICY: delete
```

### Health Checks
Both Kafka and the AI Assistant have health checks configured in docker-compose files.

### Persistent Data
To preserve Kafka data across restarts:
```bash
docker-compose down          # Don't remove volumes
docker-compose up -d
```

To reset:
```bash
docker-compose down -v       # Remove volumes
```

## Support

For issues:
1. Check logs: `docker-compose logs`
2. Verify services: `docker-compose ps`
3. Test connectivity: `telnet localhost 9092`
4. Monitor in Kafka UI: `http://localhost:8080`
