import builtins
import pytest

from ai_bot import kafka_client


def test_build_and_parse_task_payload_roundtrip():
    message = {
        "request_id": "req-1",
        "prompt": "hello world",
        "assistant_id": "default",
        "session_id": "session-1",
    }

    encoded = kafka_client.build_task_payload(message)
    assert isinstance(encoded, bytes)
    assert kafka_client.parse_task_payload(encoded) == message


def test_parse_task_payload_accepts_dict():
    payload = {"request_id": "req-2"}
    assert kafka_client.parse_task_payload(payload) == payload


def test_kafka_enabled_reads_environment(monkeypatch):
    monkeypatch.delenv("KAFKA_BOOTSTRAP_SERVERS", raising=False)
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "")
    assert kafka_client.kafka_enabled() is False

    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    assert kafka_client.kafka_enabled() is True


@pytest.mark.asyncio
async def test_create_producer_raises_if_aiokafka_missing(monkeypatch):
    orig_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "aiokafka" or name.startswith("aiokafka."):
            raise ModuleNotFoundError("No module named aiokafka")
        return orig_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(ImportError):
        await kafka_client.create_producer()


@pytest.mark.asyncio
async def test_create_consumer_raises_if_aiokafka_missing(monkeypatch):
    orig_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "aiokafka" or name.startswith("aiokafka."):
            raise ModuleNotFoundError("No module named aiokafka")
        return orig_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(ImportError):
        await kafka_client.create_consumer()
