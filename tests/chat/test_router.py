from collections.abc import AsyncIterator, Generator

import pytest
from fastapi.testclient import TestClient

from ivanpashkulev.chat.dependencies import (
    get_chat_rate_limiter,
    get_chat_service,
)
from ivanpashkulev.main import app


class FakeChatService:
    async def stream(self, message: str, history: list[dict]) -> AsyncIterator[str]:
        yield "Hello"
        yield " world"


class FakeChatRateLimiter:
    def __init__(self, retry_after_seconds: int | None = None) -> None:
        self._retry_after_seconds = retry_after_seconds

    async def retry_after_seconds(self, client_ip: str) -> int | None:
        return self._retry_after_seconds


@pytest.fixture
def client() -> Generator[TestClient]:
    app.dependency_overrides[get_chat_service] = FakeChatService
    app.dependency_overrides[get_chat_rate_limiter] = FakeChatRateLimiter

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_chat_streams_response(client: TestClient) -> None:
    response = client.post(
        "/chat",
        json={"message": "Hello", "history": []},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.text == "data: Hello\n\ndata:  world\n\ndata: [DONE]\n\n"


def test_chat_requires_message(client: TestClient) -> None:
    response = client.post("/chat", json={"history": []})

    assert response.status_code == 422


def test_chat_returns_rate_limit_response(client: TestClient) -> None:
    app.dependency_overrides[get_chat_rate_limiter] = lambda: FakeChatRateLimiter(
        retry_after_seconds=120
    )

    response = client.post("/chat", json={"message": "Hello", "history": []})

    assert response.status_code == 429
    assert response.headers["retry-after"] == "120"
    assert response.json() == {
        "detail": "Chat request limit exceeded. Please try again later."
    }


@pytest.mark.parametrize(
    ("payload", "error_code"),
    [
        (
            {"message": "a" * 1001, "history": []},
            "chat_message_limit_exceeded",
        ),
        (
            {
                "message": "Hello",
                "history": [{"role": "user", "content": "a" * 4001}],
            },
            "conversation_history_limit_exceeded",
        ),
    ],
)
def test_chat_rejects_requests_exceeding_configured_limits(
    client: TestClient,
    payload: dict,
    error_code: str,
) -> None:
    response = client.post("/chat", json=payload)

    assert response.status_code == 413
    assert response.json() == {"detail": {"code": error_code}}
