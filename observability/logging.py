import logging
import json
import sys
from typing import Dict, Any, Optional
from datetime import datetime
import os

class GenAILogFormatter(logging.Formatter):
    """Custom formatter for GenAI observability logs."""

    def format(self, record: logging.LogRecord) -> str:
        # Add GenAI-specific fields
        if not hasattr(record, 'genai_context'):
            record.genai_context = {}

        # Create structured log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "component": getattr(record, 'component', 'genai'),
            "request_id": getattr(record, 'request_id', None),
            "user_id": getattr(record, 'user_id', None),
            "session_id": getattr(record, 'session_id', None),
            "model": getattr(record, 'model', None),
            "tokens_used": getattr(record, 'tokens_used', None),
            "response_time_ms": getattr(record, 'response_time_ms', None),
            "error_type": getattr(record, 'error_type', None),
        }

        # Add any additional context
        if hasattr(record, 'genai_context'):
            log_entry.update(record.genai_context)

        # Remove None values
        log_entry = {k: v for k, v in log_entry.items() if v is not None}

        return json.dumps(log_entry, default=str)

class GenAILogger:
    """Enhanced logger for GenAI observability."""

    def __init__(self, name: str = "genai"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Remove existing handlers to avoid duplicates
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # Console handler with structured formatting
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(GenAILogFormatter())
        self.logger.addHandler(console_handler)

        # File handler for persistent logs
        log_file = os.path.join(os.getcwd(), "logs", "genai.log")
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(GenAILogFormatter())
        file_handler.setLevel(logging.DEBUG)  # More detailed logging to file
        self.logger.addHandler(file_handler)

    def log_request(self, request_id: str, query: str, user_id: str = None,
                   session_id: str = None, endpoint: str = None):
        """Log an incoming GenAI request."""
        self.logger.info(
            f"Processing GenAI request",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "session_id": session_id,
                "endpoint": endpoint,
                "component": "genai_request",
                "genai_context": {
                    "query_length": len(query) if query else 0,
                    "has_query": bool(query),
                }
            }
        )

    def log_ai_interaction(self, request_id: str, model: str, tokens_used: int,
                          response_time: float, success: bool = True,
                          user_id: str = None, session_id: str = None,
                          error: str = None):
        """Log GenAI model interaction."""
        level = logging.INFO if success else logging.ERROR
        message = "GenAI interaction completed" if success else f"GenAI interaction failed: {error}"

        self.logger.log(
            level,
            message,
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "session_id": session_id,
                "model": model,
                "tokens_used": tokens_used,
                "response_time_ms": round(response_time * 1000, 2),
                "component": "genai_interaction",
                "error_type": error,
                "genai_context": {
                    "interaction_type": "query",
                    "success": success,
                }
            }
        )

    def log_token_usage(self, request_id: str, prompt_tokens: int, response_tokens: int,
                       total_tokens: int, remaining_tokens: Optional[int] = None,
                       model: str = None):
        """Log detailed token usage."""
        self.logger.info(
            f"Token usage recorded",
            extra={
                "request_id": request_id,
                "model": model,
                "component": "token_usage",
                "genai_context": {
                    "prompt_tokens": prompt_tokens,
                    "response_tokens": response_tokens,
                    "total_tokens": total_tokens,
                    "remaining_tokens": remaining_tokens,
                    "usage_percentage": (total_tokens / 128000 * 100) if total_tokens else 0,  # Assuming Gemini limit
                }
            }
        )

    def log_error(self, request_id: str, error_type: str, error_message: str,
                 user_id: str = None, session_id: str = None, context: Dict[str, Any] = None):
        """Log GenAI errors."""
        self.logger.error(
            f"GenAI error: {error_message}",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "session_id": session_id,
                "error_type": error_type,
                "component": "genai_error",
                "genai_context": context or {},
            }
        )

# Global logger instance
genai_logger = GenAILogger()