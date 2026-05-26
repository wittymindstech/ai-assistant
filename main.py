from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
import time
import logging
from datetime import datetime

from config import Config
from ai_bot.agent import query_agent_with_usage
from ai_bot.queue import PromptQueueManager

# Import observability components
from observability.middleware import GenAIMiddleware
from observability.metrics import metrics_collector
from observability.health import health_checker
from observability.logging import genai_logger
from observability.monitor import genai_monitor

app = FastAPI(title="AI Assistant API", version="1.0.0")

# Add observability middleware
app.add_middleware(GenAIMiddleware, metrics_collector=metrics_collector)

queue_manager = PromptQueueManager()

allow_origins = Config.ALLOW_ORIGINS
if allow_origins == ["*"]:
    allow_origins = ["*"]

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Query(BaseModel):
    query: str


class QueueRequest(BaseModel):
    query: str
    assistant_id: str = 'default'
    session_id: str = 'default'


@app.on_event("startup")
async def startup_event():
    await queue_manager.start()


@app.on_event("shutdown")
async def shutdown_event():
    await queue_manager.stop()


@app.post("/ask")
async def ask(q: Query, request: Request):
    request_id = getattr(request.state, 'request_id', 'unknown')

    # Log incoming request
    genai_logger.log_request(
        request_id=request_id,
        query=q.query,
        endpoint="/ask"
    )

    start_time = time.time()
    try:
        result = await query_agent_with_usage(q.query)

        # Record successful AI interaction
        response_time = time.time() - start_time
        usage = result.get('usage', {})

        metrics_collector.record_ai_interaction(
            model="gemini-2.5-flash",
            tokens_used=usage.get('total_tokens', 0),
            response_time=response_time,
            success=True
        )

        # Log successful interaction
        genai_logger.log_ai_interaction(
            request_id=request_id,
            model="gemini-2.5-flash",
            tokens_used=usage.get('total_tokens', 0),
            response_time=response_time,
            success=True
        )

        # Log token usage details
        if usage:
            genai_logger.log_token_usage(
                request_id=request_id,
                prompt_tokens=usage.get('prompt_tokens', 0),
                response_tokens=usage.get('response_tokens', 0),
                total_tokens=usage.get('total_tokens', 0),
                remaining_tokens=usage.get('remaining_tokens'),
                model="gemini-2.5-flash"
            )

        return result

    except Exception as e:
        response_time = time.time() - start_time

        # Record failed AI interaction
        metrics_collector.record_ai_interaction(
            model="gemini-2.5-flash",
            tokens_used=0,
            response_time=response_time,
            success=False
        )

        # Log error
        genai_logger.log_error(
            request_id=request_id,
            error_type=type(e).__name__,
            error_message=str(e),
            context={"endpoint": "/ask", "query_length": len(q.query)}
        )

        raise HTTPException(status_code=500, detail=f"AI processing failed: {str(e)}")


@app.post("/enqueue")
async def enqueue(q: QueueRequest):
    task = await queue_manager.enqueue(
        prompt=q.query,
        assistant_id=q.assistant_id,
        session_id=q.session_id,
    )
    return {
        'request_id': task.request_id,
        'status': task.status,
        'assistant_id': task.assistant_id,
        'session_id': task.session_id,
    }


@app.get("/queue/{request_id}")
async def get_queue_status(request_id: str):
    task = queue_manager.get_task(request_id)
    if not task:
        raise HTTPException(status_code=404, detail='Request ID not found')
    return {
        'request_id': task.request_id,
        'status': task.status,
        'assistant_id': task.assistant_id,
        'session_id': task.session_id,
        'prompt': task.prompt,
        'result': task.result,
        'error': task.error,
        'metadata': task.metadata,
    }


@app.get("/queue")
async def list_queue_tasks():
    tasks = queue_manager.list_tasks()
    return {
        'pending': queue_manager.pending_count(),
        'tasks': [
            {
                'request_id': task.request_id,
                'status': task.status,
                'assistant_id': task.assistant_id,
                'session_id': task.session_id,
            }
            for task in tasks.values()
        ],
    }


# ===== OBSERVABILITY ENDPOINTS =====

@app.get("/health")
async def health_check():
    """Comprehensive health check for GenAI services."""
    health_status = await health_checker.check_health()
    return health_status


@app.get("/metrics")
async def get_metrics():
    """Prometheus-compatible metrics endpoint."""
    return Response(
        content=metrics_collector.get_prometheus_metrics(),
        media_type="text/plain; charset=utf-8"
    )


@app.get("/metrics/json")
async def get_metrics_json():
    """JSON metrics endpoint for monitoring dashboards."""
    return metrics_collector.get_metrics_summary()


@app.get("/monitoring")
async def get_monitoring_report():
    """Comprehensive monitoring report with alerts."""
    return genai_monitor.get_monitoring_report(metrics_collector, health_checker)


@app.post("/observability/log-metrics")
async def log_current_metrics():
    """Manually trigger metrics logging (for debugging)."""
    metrics_collector.log_metrics_summary()
    return {"status": "Metrics logged", "timestamp": datetime.utcnow().isoformat()}


# Remove duplicate CORS middleware (already added at top)
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
