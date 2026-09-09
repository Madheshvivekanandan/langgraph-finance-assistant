"""API tests for the SSE chat endpoint and its availability status."""

import json
import uuid

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy.orm import Session, sessionmaker

from app.graphs.chat.graph import build_chat_agent
from app.main import create_app
from tests.fakes.fake_chat_model import FakeChatModel


def _sse_events(body: str) -> list[tuple[str, dict[str, object]]]:
    """Parse `event:`/`data:` frame pairs out of a raw SSE response body."""
    events = []
    event_name = None
    for line in body.split("\n"):
        if line.startswith("event: "):
            event_name = line.removeprefix("event: ")
        elif line.startswith("data: "):
            assert event_name is not None
            events.append((event_name, json.loads(line.removeprefix("data: "))))
    return events


def test_post_chat_streams_tokens_and_terminates_with_done(
    session_factory: sessionmaker[Session], chat_checkpointer: PostgresSaver
) -> None:
    fake = FakeChatModel([AIMessage(content="hello there")])
    with TestClient(create_app()) as test_client:
        test_client.app.state.chat_agent = build_chat_agent(
            session_factory, fake, checkpointer=chat_checkpointer
        )

        response = test_client.post(
            "/api/v1/chat", json={"message": "hi", "thread_id": str(uuid.uuid4())}
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = _sse_events(response.text)

    token_events = [data for name, data in events if name == "token"]
    assert token_events  # at least one token frame
    assert all(isinstance(data["text"], str) for data in token_events)
    assert "".join(str(data["text"]) for data in token_events) == "hello there"
    assert events[-1] == ("done", {})


def test_post_chat_data_payloads_are_valid_json(
    session_factory: sessionmaker[Session], chat_checkpointer: PostgresSaver
) -> None:
    fake = FakeChatModel([AIMessage(content="ok")])
    with TestClient(create_app()) as test_client:
        test_client.app.state.chat_agent = build_chat_agent(
            session_factory, fake, checkpointer=chat_checkpointer
        )

        response = test_client.post(
            "/api/v1/chat", json={"message": "hi", "thread_id": str(uuid.uuid4())}
        )

    data_lines = [line for line in response.text.split("\n") if line.startswith("data: ")]
    assert data_lines
    for line in data_lines:
        json.loads(line.removeprefix("data: "))  # must not raise


def test_chat_status_reports_available_when_a_model_is_configured(
    session_factory: sessionmaker[Session], chat_checkpointer: PostgresSaver
) -> None:
    fake = FakeChatModel([])
    with TestClient(create_app()) as test_client:
        test_client.app.state.chat_agent = build_chat_agent(
            session_factory, fake, checkpointer=chat_checkpointer
        )

        response = test_client.get("/api/v1/chat/status")

    assert response.json() == {"available": True}


def test_chat_status_and_post_report_unavailable_with_no_model_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.main as main_module

    monkeypatch.setattr(main_module, "build_chat_model", lambda: None)

    with TestClient(create_app()) as test_client:
        status_response = test_client.get("/api/v1/chat/status")
        chat_response = test_client.post("/api/v1/chat", json={"message": "hi"})

    assert status_response.json() == {"available": False}
    assert chat_response.status_code == 503
    assert chat_response.headers["content-type"].startswith("application/problem+json")
    assert chat_response.json()["code"] == "CHAT_UNAVAILABLE"


def test_blank_message_is_rejected_before_any_agent_code_runs() -> None:
    with TestClient(create_app()) as test_client:
        response = test_client.post("/api/v1/chat", json={"message": "   "})

    assert response.status_code == 422


def test_a_non_uuid_thread_id_is_rejected() -> None:
    with TestClient(create_app()) as test_client:
        response = test_client.post(
            "/api/v1/chat", json={"message": "hi", "thread_id": "not-a-uuid"}
        )

    assert response.status_code == 422
