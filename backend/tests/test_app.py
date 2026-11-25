from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import Config, create_app


def make_config(tmp_path: Path, *, simulation: bool = True) -> Config:
    return Config(
        mode="litellm",
        keys=("first-key", "second-key"),
        model="test/model",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        allowed_origins=("http://localhost:3000",),
        failure_simulation=simulation,
    )


def response(text: str = "hello"):
    return {
        "model": "test/model",
        "choices": [{"message": {"content": text}}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 3},
    }


def test_health_and_offline_demo_mode(tmp_path):
    config = Config(
        mode="mock",
        keys=("demo-one", "demo-two"),
        model="demo/mock-chat",
        database_url="sqlite:///:memory:",
        allowed_origins=("http://localhost:3000",),
        failure_simulation=True,
    )
    app = create_app(config)
    with TestClient(app) as client:
        health = client.get("/health")
        chat = client.post(
            "/chat",
            json={"session_id": "demo", "message": "Capital of France?"},
        )

    assert health.json() == {
        "status": "ok",
        "keys_configured": 2,
        "models_configured": 1,
        "cache_enabled": True,
    }
    assert chat.json()["reply"] == "The capital of France is Paris."
    assert chat.json()["metadata"]["model"] == "demo/mock-chat"


def test_single_key_and_model_fallback(tmp_path):
    calls = []

    async def fake_completion(**kwargs):
        calls.append(kwargs["model"])
        if kwargs["model"] == "test/primary":
            raise RuntimeError("model unavailable")
        return {
            "model": kwargs["model"],
            "choices": [{"message": {"content": "Fallback reply"}}],
            "usage": {"prompt_tokens": 9, "completion_tokens": 2},
        }

    config = Config(
        mode="litellm",
        keys=("only-key",),
        model="test/primary",
        fallback_models=("test/fallback",),
        database_url=f"sqlite:///{tmp_path / 'single.db'}",
        allowed_origins=("http://localhost:3000",),
        failure_simulation=False,
    )
    app = create_app(config, completion=fake_completion)
    with TestClient(app) as client:
        health = client.get("/health")
        chat = client.post(
            "/chat",
            json={"session_id": "fallback", "message": "hello"},
        )

    assert health.status_code == 200
    assert health.json()["keys_configured"] == 1
    assert health.json()["models_configured"] == 2
    assert calls == ["test/primary", "test/fallback"]
    assert chat.status_code == 200
    assert chat.json()["metadata"]["model"] == "test/fallback"
    assert chat.json()["metadata"]["fallback_attempts"] == 1


def test_cache_works_across_sessions_and_keeps_usage(tmp_path):
    calls = []

    async def fake_completion(**kwargs):
        calls.append(kwargs)
        return response("Paris")

    app = create_app(make_config(tmp_path), completion=fake_completion)
    with TestClient(app) as client:
        first = client.post(
            "/chat",
            json={"session_id": "one", "message": "Capital of France?"},
        )
        second = client.post(
            "/chat",
            json={"session_id": "two", "message": "Capital of France?"},
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(calls) == 1
    assert first.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    cached = second.json()["metadata"]
    assert cached["resolution_source"] == "LLM_CACHE"
    assert cached["key_id"] is None
    assert cached["input_tokens"] == 12
    assert cached["output_tokens"] == 3
    assert cached["latency_ms"] < first.json()["metadata"]["latency_ms"]


def test_failover_and_all_keys_failed_are_not_saved(tmp_path):
    used_keys = []

    async def fake_completion(**kwargs):
        used_keys.append(kwargs["api_key"])
        return response("A real answer")

    app = create_app(make_config(tmp_path), completion=fake_completion)
    with TestClient(app) as client:
        success = client.post(
            "/chat",
            headers={"X-Simulate-Failure": "key_1=429"},
            json={"session_id": "fallback", "message": "try fallback"},
        )
        failed = client.post(
            "/chat",
            headers={"X-Simulate-Failure": "*=429"},
            json={"session_id": "empty", "message": "no providers"},
        )
        history = client.get("/sessions/empty/messages")

    assert success.status_code == 200
    assert used_keys == ["second-key"]
    assert success.json()["metadata"]["key_id"] == "key_2"
    assert success.json()["metadata"]["fallback_attempts"] == 1
    assert failed.status_code == 503
    assert failed.json() == {"detail": "all providers unavailable"}
    assert history.status_code == 404


def test_history_contains_prior_turns_and_assistant_metadata(tmp_path):
    seen_messages = []

    async def fake_completion(**kwargs):
        seen_messages.append(kwargs["messages"])
        return response("Reply")

    app = create_app(make_config(tmp_path), completion=fake_completion)
    with TestClient(app) as client:
        client.post(
            "/chat",
            json={"session_id": "multi", "message": "first question"},
        )
        client.post(
            "/chat",
            json={"session_id": "multi", "message": "second question"},
        )
        history = client.get("/sessions/multi/messages")

    assert seen_messages[1][-2:] == [
        {"role": "assistant", "content": "Reply"},
        {"role": "user", "content": "second question"},
    ]
    messages = history.json()["messages"]
    assert [item["role"] for item in messages] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert messages[1]["metadata"]["input_tokens"] == 12


@pytest.mark.parametrize(
    "payload",
    [
        {"session_id": "s1", "message": "   "},
        {"session_id": " ", "message": "hello"},
        {"session_id": "s1", "message": "x" * 4001},
    ],
)
def test_invalid_messages_return_422(tmp_path, payload):
    app = create_app(make_config(tmp_path))
    with TestClient(app) as client:
        result = client.post("/chat", json=payload)
    assert result.status_code == 422
