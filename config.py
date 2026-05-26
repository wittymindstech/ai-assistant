import os
from typing import List


def _parse_csv(value: str, fallback: str = "*") -> List[str]:
    if value is None:
        return [fallback] if fallback else []
    return [item.strip() for item in value.split(",") if item.strip()]


class Config:
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production").lower()
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "").strip()
    if ENVIRONMENT == "production" and not GOOGLE_API_KEY:
        raise EnvironmentError(
            "GOOGLE_API_KEY is required in production. Set the environment variable before starting the service."
        )

    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    KAFKA_TASK_TOPIC: str = os.getenv("KAFKA_TASK_TOPIC", "assistant_tasks")
    KAFKA_RESPONSE_TOPIC: str = os.getenv("KAFKA_RESPONSE_TOPIC", "assistant_responses")
    KAFKA_CONSUMER_GROUP: str = os.getenv("KAFKA_CONSUMER_GROUP", "assistant_agent_group")
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8001")
    ALLOW_ORIGINS: List[str] = _parse_csv(os.getenv("ALLOW_ORIGINS", "*"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8001"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
