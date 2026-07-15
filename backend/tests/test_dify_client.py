from collections.abc import Mapping
from typing import Any

import pytest

from utils.dify_client import DifyClient, DifyConfigError, DifyHTTPError


class FakeResponse:
    def __init__(
        self,
        status_code: int = 200,
        body: dict[str, Any] | None = None,
        text: str = "",
    ) -> None:
        self.status_code = status_code
        self._body = body if body is not None else {}
        self.text = text

    def json(self) -> dict[str, Any]:
        return self._body


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.request: dict[str, Any] | None = None

    def post(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        json: Mapping[str, Any],
        timeout: float,
    ) -> FakeResponse:
        self.request = {
            "url": url,
            "headers": headers,
            "json": json,
            "timeout": timeout,
        }
        return self.response


def test_send_chat_message_posts_expected_payload() -> None:
    response_body = {
        "event": "message",
        "answer": "hello",
    }
    session = FakeSession(FakeResponse(body=response_body))
    client = DifyClient(
        api_key="test-token",
        url="https://localhost:3000/v1/chat-messages",
        session=session,
        timeout=3,
    )

    result = client.send_chat_message(
        query="hello",
        user="user-1",
        inputs={"city": "Shanghai"},
        files=[
            {
                "type": "image",
                "transfer_method": "remote_url",
                "url": "https://example.com/a.png",
            }
        ],
        auto_generate_name=False,
    )

    assert result == response_body
    assert session.request == {
        "url": "https://localhost:3000/v1/chat-messages",
        "headers": {
            "Authorization": "Bearer test-token",
            "Content-Type": "application/json",
        },
        "json": {
            "inputs": {"city": "Shanghai"},
            "query": "hello",
            "response_mode": "blocking",
            "user": "user-1",
            "files": [
                {
                    "type": "image",
                    "transfer_method": "remote_url",
                    "url": "https://example.com/a.png",
                }
            ],
            "auto_generate_name": False,
        },
        "timeout": 3,
    }


def test_run_workflow_posts_to_configured_url() -> None:
    response_body = {
        "workflow_run_id": "run-1",
        "data": {"outputs": {"answer": "done"}},
    }
    session = FakeSession(FakeResponse(body=response_body))
    client = DifyClient(
        api_key="test-token",
        url="https://localhost:3000/v1/workflows/run",
        session=session,
        timeout=3,
    )

    result = client.run_workflow(
        user="user-1",
        inputs={"city": "Shanghai"},
    )

    assert result == response_body
    assert session.request == {
        "url": "https://localhost:3000/v1/workflows/run",
        "headers": {
            "Authorization": "Bearer test-token",
            "Content-Type": "application/json",
        },
        "json": {
            "inputs": {"city": "Shanghai"},
            "response_mode": "blocking",
            "user": "user-1",
        },
        "timeout": 3,
    }


def test_missing_api_key_raises_config_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DIFY_API_KEY", raising=False)
    monkeypatch.delenv("Hikari_key", raising=False)

    with pytest.raises(DifyConfigError):
        DifyClient()


def test_send_chat_message_raises_http_error_with_response_detail() -> None:
    session = FakeSession(
        FakeResponse(
            status_code=400,
            body={"code": "invalid_param", "message": "query is required"},
            text='{"code":"invalid_param","message":"query is required"}',
        )
    )
    client = DifyClient(api_key="test-token", session=session)

    with pytest.raises(DifyHTTPError) as exc_info:
        client.send_chat_message(query="hello", user="user-1")

    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code == "invalid_param"
    assert "query is required" in str(exc_info.value)
