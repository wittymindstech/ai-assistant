import time
import logging
from typing import Dict, Any, Optional
from collections import defaultdict, deque
import threading
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class GenAIMetricsCollector:
    """Collects and exposes GenAI-specific metrics."""

    def __init__(self, max_history_size: int = 1000):
        self.max_history_size = max_history_size
        self._lock = threading.Lock()

        # Request metrics
        self.request_count = defaultdict(int)
        self.request_duration = defaultdict(list)  # Keep last N durations
        self.error_count = defaultdict(int)

        # GenAI specific metrics
        self.ai_requests_total = 0
        self.ai_tokens_used = 0
        self.ai_response_times = deque(maxlen=max_history_size)
        self.ai_error_rate = 0.0

        # Model-specific metrics
        self.model_usage = defaultdict(int)
        self.model_errors = defaultdict(int)

        # User/session metrics
        self.active_users = set()
        self.session_count = 0

        logger.info("GenAI Metrics Collector initialized")

    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record an API request."""
        with self._lock:
            key = f"{method}_{endpoint}"
            self.request_count[key] += 1

            # Keep only recent durations
            if len(self.request_duration[key]) >= 100:
                self.request_duration[key].pop(0)
            self.request_duration[key].append(duration)

    def record_error(self, method: str, endpoint: str, error_type: str, duration: float):
        """Record an error."""
        with self._lock:
            key = f"{method}_{endpoint}"
            self.error_count[key] += 1
            self.record_request(method, endpoint, 500, duration)

    def record_ai_interaction(self, model: str, tokens_used: int, response_time: float,
                            user_id: str = None, session_id: str = None, success: bool = True):
        """Record a GenAI model interaction."""
        with self._lock:
            self.ai_requests_total += 1
            self.ai_tokens_used += tokens_used
            self.ai_response_times.append(response_time)

            self.model_usage[model] += 1

            if not success:
                self.model_errors[model] += 1

            if user_id:
                self.active_users.add(user_id)

            if session_id:
                self.session_count += 1

            # Update error rate
            total_requests = sum(self.model_usage.values())
            total_errors = sum(self.model_errors.values())
            self.ai_error_rate = total_errors / total_requests if total_requests > 0 else 0

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics."""
        with self._lock:
            # Calculate averages
            avg_response_time = (sum(self.ai_response_times) / len(self.ai_response_times)
                               if self.ai_response_times else 0)

            # Calculate request rate (requests per minute over last hour)
            recent_requests = sum(count for key, count in self.request_count.items()
                                if 'ask' in key or 'enqueue' in key)

            return {
                "timestamp": datetime.utcnow().isoformat(),
                "ai_metrics": {
                    "total_requests": self.ai_requests_total,
                    "total_tokens_used": self.ai_tokens_used,
                    "average_response_time_ms": round(avg_response_time * 1000, 2),
                    "error_rate": round(self.ai_error_rate * 100, 2),
                    "active_users": len(self.active_users),
                    "total_sessions": self.session_count,
                },
                "model_metrics": dict(self.model_usage),
                "model_errors": dict(self.model_errors),
                "api_metrics": {
                    "request_counts": dict(self.request_count),
                    "error_counts": dict(self.error_count),
                },
                "health_status": "healthy" if self.ai_error_rate < 0.1 else "degraded"
            }

    def get_prometheus_metrics(self) -> str:
        """Generate Prometheus-compatible metrics output."""
        metrics = []
        summary = self.get_metrics_summary()

        # AI Metrics
        ai = summary["ai_metrics"]
        metrics.extend([
            f'# HELP genai_requests_total Total number of GenAI requests',
            f'# TYPE genai_requests_total counter',
            f'genai_requests_total {ai["total_requests"]}',
            f'',
            f'# HELP genai_tokens_used_total Total tokens used by GenAI',
            f'# TYPE genai_tokens_used_total counter',
            f'genai_tokens_used_total {ai["total_tokens_used"]}',
            f'',
            f'# HELP genai_response_time_average_ms Average response time in milliseconds',
            f'# TYPE genai_response_time_average_ms gauge',
            f'genai_response_time_average_ms {ai["average_response_time_ms"]}',
            f'',
            f'# HELP genai_error_rate_percent Error rate as percentage',
            f'# TYPE genai_error_rate_percent gauge',
            f'genai_error_rate_percent {ai["error_rate"]}',
        ])

        # Model metrics
        for model, count in summary["model_metrics"].items():
            metrics.extend([
                f'# HELP genai_model_requests_total Requests per model',
                f'# TYPE genai_model_requests_total counter',
                f'genai_model_requests_total{{model="{model}"}} {count}',
            ])

        return '\n'.join(metrics)

    def log_metrics_summary(self):
        """Log a summary of current metrics."""
        summary = self.get_metrics_summary()
        logger.info(f"GenAI Metrics Summary: {json.dumps(summary, indent=2)}")

# Global metrics collector instance
metrics_collector = GenAIMetricsCollector()