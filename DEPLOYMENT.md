# Complete Deployment Guide

## 🚀 One-Command Deployment

```bash
# Make script executable and run
chmod +x deploy.sh
./deploy.sh
```

This starts all components:
- ✅ Zookeeper (Kafka coordination)
- ✅ Kafka Broker (Message queue)
- ✅ Kafka UI (Monitoring dashboard)
- ✅ AI Assistant API (FastAPI server with Kafka integration)

## 📊 Service Endpoints

| Service | URL | Purpose |
|---------|-----|---------|
| **Ecommerce Frontend** | http://localhost:4200 | Chat UI for AI Assistant |
| **AI Assistant API** | http://localhost:8001 | Main REST API |
| **API Documentation** | http://localhost:8001/docs | Interactive API docs |
| **Queue Status** | http://localhost:8001/queue | Check queue health |
| **Kafka UI** | http://localhost:8080 | Monitor Kafka topics |

## 🖥️ Accessing the Frontend

After deployment, open your browser and go to:

**http://localhost:4200**

This will load the **Ecommerce Products Bot** - a chat interface that connects to your AI Assistant API.

### Frontend Features
- **Real-time chat** with the AI Assistant
- **Product inquiry interface** for ecommerce scenarios
- **Responsive design** for desktop and mobile
- **Direct API integration** with your FastAPI backend

### How it Works
1. User types a message in the chat box
2. Frontend sends POST request to `http://localhost:8001/ask`
3. AI Assistant processes the query using Gemini AI
4. Response appears in the chat interface

## 🧪 Testing the Deployment

### Test Direct API Call
```bash
curl -X POST http://localhost:8001/ask \
  -H "Content-Type: application/json" \
  -d '{"query":"What documents are available?"}'
```

### Test Queued Processing
```bash
curl -X POST http://localhost:8001/enqueue \
  -H "Content-Type: application/json" \
  -d '{"query":"Analyze the resume for technical skills"}'
```

Response includes `request_id` for tracking.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐
│   Client Apps   │────│  AI Assistant    │
│                 │    │  FastAPI Server  │
│ - Web Browsers  │    │  Port: 8001      │
│ - Mobile Apps   │    └─────────┬────────┘
│ - Other APIs    │              │
└─────────────────┘              │
                                 │
                    ┌────────────▼────────────┐
                    │                         │
          ┌─────────┴─────────┐    ┌─────────┴─────────┐
          │   Kafka Queue     │    │   Document       │
          │   (Async Tasks)   │    │   Processing     │
          │                   │    │   Engine         │
          │ • assistant_tasks │    │ • PDF Analysis   │
          │ • assistant_resp. │    │ • OCR Images     │
          └───────────────────┘    │ • Link Extraction│
                                   └───────────────────┘
```

## 🔧 Manual Deployment Options

### Option 1: Docker Compose (Recommended)

```bash
# Start everything
docker-compose -f docker-compose.full.yml up -d

# View logs
docker-compose -f docker-compose.full.yml logs -f

# Stop everything
docker-compose -f docker-compose.full.yml down
```

### Option 2: Local Development

```bash
# Terminal 1: Start Kafka infrastructure
docker-compose up -d

# Terminal 2: Run AI Assistant
bash scripts/run_with_kafka.sh
```

### Option 3: Production Deployment

For production, consider:

#### Docker Swarm
```bash
docker stack deploy -c docker-compose.full.yml ai-assistant
```

#### Kubernetes
```bash
kubectl apply -f k8s/
```

#### Cloud Platforms
- **AWS**: ECS/Fargate + RDS for Kafka
- **GCP**: Cloud Run + Cloud Pub/Sub
- **Azure**: Container Instances + Event Hubs

## 📁 Project Structure

```
ai-assistant/
├── ai_bot/              # AI agent core
│   ├── agent.py        # Gemini integration
│   ├── queue.py        # Kafka queue manager
│   └── kafka_client.py # Kafka utilities
├── main.py             # FastAPI application
├── Dockerfile          # Container definition
├── docker-compose.full.yml  # Complete stack
├── scripts/            # Deployment scripts
│   ├── deploy.sh      # One-click deployment
│   ├── run_with_kafka.sh
│   └── start_kafka.sh
└── data/              # Document storage
    ├── pdfs/          # PDF documents
    └── images/        # Images for OCR
```

## 🔐 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_API_KEY` | (required) | Gemini API key |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:29092` | Kafka connection |
| `KAFKA_TASK_TOPIC` | `assistant_tasks` | Task queue topic |
| `KAFKA_RESPONSE_TOPIC` | `assistant_responses` | Response topic |
| `KAFKA_CONSUMER_GROUP` | `assistant_agent_group` | Consumer group |

## 📈 Monitoring & Observability

### Health Checks
- AI Assistant: `GET /queue` - Returns queue status
- Kafka: `GET /health` on Kafka UI
- Container health checks built into Docker Compose

### Logs
```bash
# All services
docker-compose -f docker-compose.full.yml logs -f

# Specific service
docker-compose -f docker-compose.full.yml logs -f ai-assistant
```

### Metrics
- Kafka UI provides topic monitoring
- FastAPI `/metrics` endpoint (if prometheus added)
- Container resource usage via `docker stats`

## 🚀 Scaling Considerations

### Horizontal Scaling
- Run multiple AI Assistant instances
- Kafka handles load distribution
- Use Kubernetes for auto-scaling

### Vertical Scaling
- Increase container CPU/memory limits
- Use more powerful Kafka brokers
- Add Redis for caching if needed

## 🔄 CI/CD Integration

### GitHub Actions Example
```yaml
name: Deploy AI Assistant
on: [push]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to production
        run: |
          echo "Deploying AI Assistant..."
          # Add your deployment commands here
```

## 🐛 Troubleshooting

### Common Issues

**"Connection refused" errors:**
- Ensure Docker is running
- Wait for services to be healthy: `docker-compose ps`

**Kafka connection issues:**
- Check Kafka UI at http://localhost:8080
- Verify network connectivity: `docker network ls`

**AI Assistant not responding:**
- Check logs: `docker-compose logs ai-assistant`
- Verify GOOGLE_API_KEY is set
- Test direct API: `curl http://localhost:8001/queue`

**Port conflicts:**
- Change ports in docker-compose.full.yml
- Stop conflicting services

### Debug Commands
```bash
# Check service status
docker-compose -f docker-compose.full.yml ps

# Restart specific service
docker-compose -f docker-compose.full.yml restart ai-assistant

# Enter container
docker-compose -f docker-compose.full.yml exec ai-assistant bash

# Clean restart
docker-compose -f docker-compose.full.yml down -v
docker-compose -f docker-compose.full.yml up -d --build
```