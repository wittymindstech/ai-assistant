import asyncio
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class GenAIHealthChecker:
    """Health checker for GenAI models and services."""

    def __init__(self):
        self.last_check = None
        self.check_interval = 60  # seconds
        self.health_status = {
            "overall": "unknown",
            "model_available": False,
            "api_accessible": False,
            "last_successful_request": None,
            "consecutive_failures": 0,
            "average_response_time": None,
            "token_limits": {},
        }
        self.response_times = []

    async def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        now = datetime.utcnow()

        # Don't check too frequently
        if self.last_check and (now - self.last_check).seconds < self.check_interval:
            return self.health_status

        self.last_check = now
        logger.info("Performing GenAI health check...")

        try:
            # Test basic model availability
            from ai_bot.agent import query_agent_with_usage

            start_time = time.time()
            # Simple test query
            result = await query_agent_with_usage("Hello", user_id="health_check", session_id="health_check")
            response_time = time.time() - start_time

            # Update health status
            self.health_status.update({
                "overall": "healthy",
                "model_available": True,
                "api_accessible": True,
                "last_successful_request": now.isoformat(),
                "consecutive_failures": 0,
            })

            # Track response times
            self.response_times.append(response_time)
            if len(self.response_times) > 10:  # Keep last 10
                self.response_times.pop(0)

            self.health_status["average_response_time"] = sum(self.response_times) / len(self.response_times)

            # Extract usage info
            if "usage" in result:
                usage = result["usage"]
                self.health_status["token_limits"] = {
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "response_tokens": usage.get("response_tokens"),
                    "total_tokens": usage.get("total_tokens"),
                    "remaining_tokens": usage.get("remaining_tokens"),
                }

            logger.info(f"GenAI health check passed in {response_time:.2f}s")

        except Exception as e:
            self.health_status["consecutive_failures"] += 1
            self.health_status.update({
                "overall": "unhealthy" if self.health_status["consecutive_failures"] > 3 else "degraded",
                "model_available": False,
                "api_accessible": False,
                "last_error": str(e),
                "error_timestamp": now.isoformat(),
            })

            logger.error(f"GenAI health check failed: {str(e)}")

        return self.health_status

    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status without performing a new check."""
        return self.health_status

# Global health checker instance
health_checker = GenAIHealthChecker()