import pytest


@pytest.fixture(autouse=True)
def disable_kafka_env(monkeypatch):
    monkeypatch.delenv("KAFKA_BOOTSTRAP_SERVERS", raising=False)
    yield
