from collections.abc import AsyncIterator, Generator

import pytest
from fastapi.testclient import TestClient

from ivanpashkulev.chat.dependencies import get_chat_service
from ivanpashkulev.main import app


class FakeChatService:
    async def stream(self, message: str, history: list[dict]) -> AsyncIterator[str]:
        yield "Hello"
        yield " world"


@pytest.fixture
def client() -> Generator[TestClient]:
    app.dependency_overrides[get_chat_service] = FakeChatService

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
