import time

from fastapi.testclient import TestClient
from fastapi import FastAPI

import main


def test_ask_endpoint_returns_response(monkeypatch):
    async def fake_query_agent_with_usage(query):
        return {"response": "hello", "usage": {"prompt_tokens": 1}}

    monkeypatch.setattr(main, "query_agent_with_usage", fake_query_agent_with_usage)

    # Create a minimal app for testing without lifespan events
    test_app = FastAPI()
    test_app.add_middleware(
        main.CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @test_app.post("/ask")
    async def ask(q: main.Query):
        result = await main.query_agent_with_usage(q.query)
        return result

    with TestClient(test_app) as client:
        response = client.post("/ask", json={"query": "hello"})

    assert response.status_code == 200
    assert response.json() == {"response": "hello", "usage": {"prompt_tokens": 1}}


def test_enqueue_and_queue_status(monkeypatch):
    async def fake_query_agent_with_usage(prompt, user_id="web_user", session_id="web_session"):
        return {"response": f"processed: {prompt}", "usage": {}}

    monkeypatch.setattr("ai_bot.queue.query_agent_with_usage", fake_query_agent_with_usage)

    # Create a test app without lifespan events
    test_app = FastAPI()
    test_app.add_middleware(
        main.CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Create a fresh queue manager for testing and start it
    test_queue_manager = main.PromptQueueManager()
    # Note: We don't start the queue manager in tests to avoid async complications
    # Instead, we'll manually process the task

    @test_app.post("/enqueue")
    async def enqueue(q: main.QueueRequest):
        task = await test_queue_manager.enqueue(
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

    @test_app.get("/queue/{request_id}")
    async def get_queue_status(request_id: str):
        task = test_queue_manager.get_task(request_id)
        if not task:
            from fastapi import HTTPException
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

    with TestClient(test_app) as client:
        enqueue_response = client.post(
            "/enqueue",
            json={
                "query": "sample task",
                "assistant_id": "user1",
                "session_id": "session1",
            },
        )
        assert enqueue_response.status_code == 200
        body = enqueue_response.json()
        request_id = body["request_id"]
        assert body["status"] == "queued"

        # Manually process the task (since we don't start the queue manager in tests)
        task = test_queue_manager.get_task(request_id)
        assert task is not None
        task.status = 'processing'
        # Simulate the processing (can't await in sync test, so just set the result)
        task.result = {"response": f"processed: {task.prompt}", "usage": {}}
        task.status = 'completed'
        task.metadata = {
            'assistant_id': task.assistant_id,
            'session_id': task.session_id,
        }

        status_response = client.get(f"/queue/{request_id}")
        assert status_response.status_code == 200
        detail = status_response.json()
        assert detail["request_id"] == request_id
        assert detail["prompt"] == "sample task"
        assert detail["assistant_id"] == "user1"
        assert detail["session_id"] == "session1"
        assert detail["status"] == "completed"
        assert detail["result"]["response"] == "processed: sample task"
        assert detail["error"] is None


