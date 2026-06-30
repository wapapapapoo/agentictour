"""
    通过调用 Dify API 来运行工作流和发送聊天消息的客户端。
    通过 init 一个 DifyClient 实例来使用。

    强制需要 api_key 和 url 参数。
    同时可传入一个有 post 方法的 session 对象和 timeout 参数。
    函数将 dify 的返回值解析为 json 并返回,若 dify 返回非 200 状态码则抛出异常。
"""
from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from typing import Any, Literal, Protocol

import requests

DEFAULT_DIFY_URL = "https://localhost:3000/v1/chat-messages"
DEFAULT_TIMEOUT = 30.0


class DifyError(Exception):
    """Base exception for Dify client failures."""


class DifyConfigError(DifyError):
    """Raised when required client configuration is missing or invalid."""


class DifyRequestError(DifyError):
    """Raised when the request cannot reach Dify."""


class DifyTimeoutError(DifyRequestError):
    """Raised when a Dify request times out."""


class DifyHTTPError(DifyError):
    """Raised when Dify returns an unsuccessful HTTP response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        error_code: str | None = None,
        response_body: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.response_body = response_body


class DifyResponseError(DifyError):
    """Raised when Dify returns a response that cannot be parsed as expected."""


class SupportsPost(Protocol):
    def post(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        json: Mapping[str, Any],
        timeout: float,
    ) -> Any:
        """Subset of requests.Session used by this client."""


class DifyClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        session: SupportsPost | None = None,
    ) -> None:
        resolved_api_key = (
            api_key or os.getenv("DIFY_API_KEY") or os.getenv("Hikari_key") or ""
        ).strip()
        if not resolved_api_key:
            raise DifyConfigError(
                "Dify API key is required. Pass api_key or set DIFY_API_KEY."
            )

        resolved_url = (url or os.getenv("DIFY_URL") or DEFAULT_DIFY_URL).strip()
        if not resolved_url.startswith(("http://", "https://")):
            raise DifyConfigError("Dify url must start with http:// or https://.")

        if timeout <= 0:
            raise DifyConfigError("Dify timeout must be greater than zero.")

        self.api_key = resolved_api_key
        self.url = resolved_url
        self.timeout = timeout
        self.session = session or requests.Session()

    def post_json(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Post a JSON payload to the configured Dify endpoint URL."""
        try:
            response = self.session.post(
                self.url,
                headers=self._headers(),
                json=dict(payload),
                timeout=self.timeout,
            )
        except requests.exceptions.Timeout as exc:
            raise DifyTimeoutError("Dify request timed out.") from exc
        except requests.exceptions.RequestException as exc:
            raise DifyRequestError(f"Dify request failed: {exc}") from exc

        if response.status_code >= 400:
            self._raise_http_error(response)

        body = self._parse_json(response)
        if not isinstance(body, dict):
            raise DifyResponseError("Dify response JSON must be an object.")

        return body

    def run_workflow(
        self,
        *,
        user: str,
        inputs: Mapping[str, Any] | None = None,
        response_mode: Literal["blocking"] = "blocking",
    ) -> dict[str, Any]:
        """Run a blocking workflow through the configured Dify workflow URL."""
        if not user.strip():
            raise ValueError("user must not be empty.")
        if response_mode != "blocking":
            raise ValueError("run_workflow currently supports only blocking mode.")

        payload: dict[str, Any] = {
            "inputs": dict(inputs or {}),
            "response_mode": response_mode,
            "user": user,
        }
        return self.post_json(payload)

    def send_chat_message(
        self,
        *,
        query: str,
        user: str,
        inputs: Mapping[str, Any] | None = None,
        conversation_id: str | None = None,
        files: Sequence[Mapping[str, Any]] | None = None,
        auto_generate_name: bool | None = None,
        response_mode: Literal["blocking"] = "blocking",
    ) -> dict[str, Any]:
        """Send a blocking chat message to the configured Dify chat URL."""
        if not query.strip():
            raise ValueError("query must not be empty.")
        if not user.strip():
            raise ValueError("user must not be empty.")
        if response_mode != "blocking":
            raise ValueError("send_chat_message currently supports only blocking mode.")

        payload: dict[str, Any] = {
            "inputs": dict(inputs or {}),
            "query": query,
            "response_mode": response_mode,
            "user": user,
        }
        if conversation_id:
            payload["conversation_id"] = conversation_id
        if files is not None:
            payload["files"] = [dict(file) for file in files]
        if auto_generate_name is not None:
            payload["auto_generate_name"] = auto_generate_name

        return self.post_json(payload)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _raise_http_error(self, response: Any) -> None:
        body = self._parse_json_or_text(response)
        error_code = body.get("code") if isinstance(body, dict) else None
        message = body.get("message") if isinstance(body, dict) else None
        if not message:
            message = getattr(response, "text", "") or "No response body."

        raise DifyHTTPError(
            f"Dify API returned HTTP {response.status_code}: {message}",
            status_code=response.status_code,
            error_code=error_code,
            response_body=body,
        )

    @staticmethod
    def _parse_json(response: Any) -> Any:
        try:
            return response.json()
        except ValueError as exc:
            raise DifyResponseError("Dify response body is not valid JSON.") from exc

    @staticmethod
    def _parse_json_or_text(response: Any) -> Any:
        try:
            return response.json()
        except ValueError:
            return getattr(response, "text", "")
