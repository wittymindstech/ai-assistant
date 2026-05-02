import asyncio

import pytest

from ai_bot.queue import PromptQueueManager


@pytest.mark.asyncio
async def test_enqueue_uses_local_queue_when_kafka_disabled(monkeypatch):
    monkeypatch.delenv("KAFKA_BOOTSTRAP_SERVERS", raising=False)

    manager = PromptQueueManager()
    assert not manager.kafka_enabled

    task = await manager.enqueue(
        prompt="find technical skills in resume",
        assistant_id="user1",
        session_id="session1",
    )

    assert task.request_id in manager.tasks
    assert task.status == "queued"
    assert manager.queue.qsize() == 1

    await manager.stop()


@pytest.mark.asyncio
async def test_worker_loop_processes_task_and_sets_result(monkeypatch):
    monkeypatch.delenv("KAFKA_BOOTSTRAP_SERVERS", raising=False)

    async def fake_query_agent_with_usage(prompt, user_id="web_user", session_id="web_session"):
        return {"response": f"processed: {prompt}", "usage": {}}

    monkeypatch.setattr("ai_bot.queue.query_agent_with_usage", fake_query_agent_with_usage)

    manager = PromptQueueManager()
    await manager.start()

    task = await manager.enqueue(
        prompt="test prompt",
        assistant_id="user2",
        session_id="session2",
    )

    await asyncio.wait_for(manager.queue.join(), timeout=5)

    assert task.status == "completed"
    assert task.result == {"response": "processed: test prompt", "usage": {}}
    assert task.metadata["assistant_id"] == "user2"
    assert task.metadata["session_id"] == "session2"

    await manager.stop()
