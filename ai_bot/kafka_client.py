import json
import os
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

KAFKA_DEFAULT_BOOTSTRAP_SERVERS = "localhost:9092"
KAFKA_TASK_TOPIC = "assistant_tasks"
KAFKA_RESPONSE_TOPIC = "assistant_responses"
KAFKA_CONSUMER_GROUP = "assistant_agent_group"


def kafka_enabled() -> bool:
    return bool(os.environ.get("KAFKA_BOOTSTRAP_SERVERS", ""))


def get_bootstrap_servers() -> str:
    return os.environ.get("KAFKA_BOOTSTRAP_SERVERS", KAFKA_DEFAULT_BOOTSTRAP_SERVERS)


def get_task_topic() -> str:
    return os.environ.get("KAFKA_TASK_TOPIC", KAFKA_TASK_TOPIC)


def get_response_topic() -> str:
    return os.environ.get("KAFKA_RESPONSE_TOPIC", KAFKA_RESPONSE_TOPIC)


def get_consumer_group() -> str:
    return os.environ.get("KAFKA_CONSUMER_GROUP", KAFKA_CONSUMER_GROUP)


async def create_producer():
    try:
        from aiokafka import AIOKafkaProducer
    except ImportError as exc:
        raise ImportError(
            "aiokafka is required for Kafka integration. Install with `pip install aiokafka`."
        ) from exc

    return AIOKafkaProducer(bootstrap_servers=get_bootstrap_servers())


async def create_consumer():
    try:
        from aiokafka import AIOKafkaConsumer
    except ImportError as exc:
        raise ImportError(
            "aiokafka is required for Kafka integration. Install with `pip install aiokafka`."
        ) from exc

    return AIOKafkaConsumer(
        get_task_topic(),
        bootstrap_servers=get_bootstrap_servers(),
        group_id=get_consumer_group(),
        enable_auto_commit=False,
        auto_offset_reset="earliest",
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )


def build_task_payload(task: Dict[str, Any]) -> bytes:
    return json.dumps(task, default=str).encode("utf-8")


def parse_task_payload(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, (bytes, bytearray)):
        return json.loads(payload.decode("utf-8"))
    if isinstance(payload, dict):
        return payload
    raise ValueError("Unsupported Kafka task payload type")
