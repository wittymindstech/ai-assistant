import os
from typing import List


def _parse_csv(value: str, fallback: str = "*") -> List[str]:
    if value is None:
        return [fallback] if fallback else []
    return [item.strip() for item in value.split(",") if item.strip()]


class Config:
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development").lower()
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "").strip()
    if ENVIRONMENT == "production" and not GOOGLE_API_KEY:
        raise EnvironmentError(
            "GOOGLE_API_KEY is required in production. Set the environment variable before starting the service."
        )

    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "")
    KAFKA_TASK_TOPIC: str = os.getenv("KAFKA_TASK_TOPIC", "assistant_tasks")
    KAFKA_RESPONSE_TOPIC: str = os.getenv("KAFKA_RESPONSE_TOPIC", "assistant_responses")
    KAFKA_CONSUMER_GROUP: str = os.getenv("KAFKA_CONSUMER_GROUP", "assistant_agent_group")
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8001")
    ALLOW_ORIGINS: List[str] = _parse_csv(os.getenv("ALLOW_ORIGINS", "*"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8001"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    MAX_PROMPT_LENGTH: int = int(os.getenv("MAX_PROMPT_LENGTH", "2000"))
    BLOCKED_PROMPT_KEYWORDS: List[str] = _parse_csv(
        os.getenv(
            "BLOCKED_PROMPT_KEYWORDS",
            "bomb,explosive,terrorist,attack,kill,shoot,steal,hack,illegal,child abuse,self-harm,suicide,rape,sexual,drug manufacture"
        ),
        fallback=""
    )
    # AWS S3 settings for production storage of assets
    S3_BUCKET: str = os.getenv("S3_BUCKET", "").strip()
    S3_PREFIX_PDFS: str = os.getenv("S3_PREFIX_PDFS", "pdfs/")
    S3_PREFIX_IMAGES: str = os.getenv("S3_PREFIX_IMAGES", "images/")
    S3_PREFIX_AUDIO: str = os.getenv("S3_PREFIX_AUDIO", "audio/")
    S3_PREFIX_DOCS: str = os.getenv("S3_PREFIX_DOCS", "docs/")
    S3_PREFIX_MISC: str = os.getenv("S3_PREFIX_MISC", "misc/")

    if ENVIRONMENT == "production" and not S3_BUCKET:
        raise EnvironmentError(
            "S3_BUCKET is required in production. Set the S3_BUCKET environment variable."
        )
