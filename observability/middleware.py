from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging
import json
from typing import Dict, Any
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class GenAIMiddleware(BaseHTTPMiddleware):
    """Middleware for GenAI observability and monitoring."""

    def __init__(self, app, metrics_collector=None):
        super().__init__(app)
        self.metrics_collector = metrics_collector

    async def dispatch(self, request: Request, call_next):
        # Generate request ID for tracing
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        # Start timing
        start_time = time.time()

        # Log incoming request
        self._log_request(request, request_id)

        # Process request
        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            # Log response
            self._log_response(response, request_id, process_time)

            # Record metrics
            if self.metrics_collector:
                self.metrics_collector.record_request(
                    method=request.method,
                    endpoint=request.url.path,
                    status_code=response.status_code,
                    duration=process_time
                )

            return response

        except Exception as e:
            process_time = time.time() - start_time
            logger.error(f"Request {request_id} failed: {str(e)}", exc_info=True)

            if self.metrics_collector:
                self.metrics_collector.record_error(
                    method=request.method,
                    endpoint=request.url.path,
                    error_type=type(e).__name__,
                    duration=process_time
                )

            raise

    def _log_request(self, request: Request, request_id: str):
        """Log incoming GenAI requests."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id,
            "method": request.method,
            "endpoint": request.url.path,
            "user_agent": request.headers.get("user-agent", "unknown"),
            "client_ip": request.client.host if request.client else "unknown",
            "component": "genai_api"
        }

        # Add query data for AI endpoints
        if request.method == "POST" and "query" in request.url.path:
            try:
                # Note: In production, you'd want to be careful about logging sensitive data
                log_data["has_query"] = True
            except:
                pass

        logger.info(f"GenAI Request: {json.dumps(log_data)}")

    def _log_response(self, response: Response, request_id: str, duration: float):
        """Log GenAI responses."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
            "component": "genai_api"
        }

        # Add usage data if available
        if hasattr(response, 'usage_data'):
            log_data.update(response.usage_data)

        log_level = "info" if response.status_code < 400 else "warning"
        getattr(logger, log_level)(f"GenAI Response: {json.dumps(log_data)}")