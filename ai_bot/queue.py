import asyncio
import json
import uuid
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, Any

from .agent import query_agent_with_usage
from guardrails import GuardRailViolation, enforce_prompt_guardrails
from .kafka_client import (
    build_task_payload,
    create_consumer,
    create_producer,
    get_response_topic,
    get_task_topic,
    kafka_enabled,
    parse_task_payload,
)

logger = logging.getLogger(__name__)


@dataclass
class PromptTask:
    request_id: str
    prompt: str
    assistant_id: str = 'default'
    session_id: str = 'default'
    status: str = 'queued'
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PromptQueueManager:
    def __init__(self):
        self.queue: Optional[asyncio.Queue[str]] = None
        self.tasks: Dict[str, PromptTask] = {}
        self._worker_task: Optional[asyncio.Task[Any]] = None
        self._kafka_consumer_task: Optional[asyncio.Task[Any]] = None
        self._running = False
        self.kafka_enabled = kafka_enabled()
        self.kafka_producer = None
        self.kafka_consumer = None

    async def start(self) -> None:
        if not self._running:
            self._running = True
            if self.queue is None:
                self.queue = asyncio.Queue()
            if self.kafka_enabled:
                self.kafka_producer = await create_producer()
                await self.kafka_producer.start()
                self.kafka_consumer = await create_consumer()
                await self.kafka_consumer.start()
                self._kafka_consumer_task = asyncio.create_task(self._kafka_consumer_loop())
                logger.info("Prompt queue manager started with Kafka integration")
            else:
                self._worker_task = asyncio.create_task(self._worker_loop())
                logger.info("Prompt queue manager started")

    async def stop(self) -> None:
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        if self._kafka_consumer_task:
            self._kafka_consumer_task.cancel()
            try:
                await self._kafka_consumer_task
            except asyncio.CancelledError:
                pass
        if self.kafka_consumer:
            await self.kafka_consumer.stop()
        if self.kafka_producer:
            await self.kafka_producer.stop()
        logger.info("Prompt queue manager stopped")

    async def enqueue(self, prompt: str, assistant_id: str = 'default', session_id: str = 'default') -> PromptTask:
        try:
            enforce_prompt_guardrails(prompt)
        except GuardRailViolation as e:
            raise ValueError(f"Prompt rejected by guard rails: {e}")

        request_id = str(uuid.uuid4())
        task = PromptTask(
            request_id=request_id,
            prompt=prompt,
            assistant_id=assistant_id,
            session_id=session_id,
            status='queued',
        )
        self.tasks[request_id] = task
        if self.queue is None:
            self.queue = asyncio.Queue()
        if self.kafka_enabled and self.kafka_producer:
            payload = build_task_payload({
                'request_id': request_id,
                'prompt': prompt,
                'assistant_id': assistant_id,
                'session_id': session_id,
            })
            await self.kafka_producer.send_and_wait(get_task_topic(), value=payload)
            logger.info(f"Published prompt {request_id} to Kafka topic {get_task_topic()}")
        else:
            await self.queue.put(request_id)
            logger.info(f"Enqueued prompt {request_id} for assistant {assistant_id}")
        return task

    async def _worker_loop(self) -> None:
        while self._running:
            request_id = await self.queue.get()
            task = self.tasks.get(request_id)
            if task is None:
                self.queue.task_done()
                continue

            task.status = 'processing'
            try:
                logger.info(f"Processing queued prompt {request_id}")
                enforce_prompt_guardrails(task.prompt)
                task.result = await query_agent_with_usage(
                    task.prompt,
                    user_id=task.assistant_id,
                    session_id=task.session_id,
                )
                task.status = 'completed'
                task.metadata = {
                    'assistant_id': task.assistant_id,
                    'session_id': task.session_id,
                }
                await self._publish_response(task)
            except GuardRailViolation as exc:
                logger.warning(f"Queued prompt {request_id} blocked by guard rails: {exc}")
                task.error = str(exc)
                task.status = 'failed'
            except Exception as exc:
                logger.error(f"Queued prompt {request_id} failed: {exc}", exc_info=True)
                task.error = str(exc)
                task.status = 'failed'
            finally:
                self.queue.task_done()

    async def _kafka_consumer_loop(self) -> None:
        try:
            async for message in self.kafka_consumer:
                if not self._running:
                    break

                payload = message.value
                await self._process_kafka_message(payload)
                await self.kafka_consumer.commit()
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error(f"Kafka consumer loop failed: {exc}", exc_info=True)
            await asyncio.sleep(1)

    async def _process_kafka_message(self, payload: Any) -> None:
        try:
            data = parse_task_payload(payload)
            request_id = data.get('request_id')
            if not request_id:
                logger.warning("Received Kafka task without request_id")
                return

            task = self.tasks.get(request_id)
            if task is None:
                task = PromptTask(
                    request_id=request_id,
                    prompt=data.get('prompt', ''),
                    assistant_id=data.get('assistant_id', 'default'),
                    session_id=data.get('session_id', 'default'),
                    status='queued',
                )
                self.tasks[request_id] = task

            task.status = 'processing'
            logger.info(f"Processing Kafka prompt {request_id}")
            enforce_prompt_guardrails(task.prompt)
            task.result = await query_agent_with_usage(
                task.prompt,
                user_id=task.assistant_id,
                session_id=task.session_id,
            )
            task.status = 'completed'
            task.metadata = {
                'assistant_id': task.assistant_id,
                'session_id': task.session_id,
            }
            await self._publish_response(task)
        except GuardRailViolation as exc:
            logger.warning(f"Kafka prompt {request_id} blocked by guard rails: {exc}")
            if request_id and self.tasks.get(request_id):
                self.tasks[request_id].error = str(exc)
                self.tasks[request_id].status = 'failed'
        except Exception as exc:
            logger.error(f"Kafka task {payload} failed: {exc}", exc_info=True)
            if isinstance(payload, dict):
                request_id = payload.get('request_id')
            else:
                request_id = None
            if request_id and self.tasks.get(request_id):
                self.tasks[request_id].error = str(exc)
                self.tasks[request_id].status = 'failed'

    async def _publish_response(self, task: PromptTask) -> None:
        if not self.kafka_enabled or not self.kafka_producer:
            return

        response_topic = get_response_topic()
        if not response_topic:
            return

        payload = build_task_payload({
            'request_id': task.request_id,
            'assistant_id': task.assistant_id,
            'session_id': task.session_id,
            'status': task.status,
            'result': task.result,
            'error': task.error,
            'metadata': task.metadata,
        })
        try:
            await self.kafka_producer.send_and_wait(response_topic, value=payload)
            logger.info(f"Published response for {task.request_id} to Kafka topic {response_topic}")
        except Exception as exc:
            logger.error(f"Failed to publish Kafka response for {task.request_id}: {exc}", exc_info=True)

    def get_task(self, request_id: str) -> Optional[PromptTask]:
        return self.tasks.get(request_id)

    def list_tasks(self) -> Dict[str, PromptTask]:
        return dict(self.tasks)

    def pending_count(self) -> int:
        return self.queue.qsize() if self.queue is not None else 0
