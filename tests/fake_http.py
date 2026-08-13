"""Minimal aiohttp-compatible fakes for testing the auth/client layers."""

from __future__ import annotations

from typing import Any

import aiohttp


class FakeResponse:
    """Stand-in for aiohttp's response context manager."""

    def __init__(
        self,
        *,
        status: int = 200,
        json_data: Any = None,
        raise_client_error: bool = False,
    ) -> None:
        self.status = status
        self._json = json_data
        self._raise_client_error = raise_client_error

    async def __aenter__(self) -> "FakeResponse":
        if self._raise_client_error:
            raise aiohttp.ClientError("boom")
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise aiohttp.ClientResponseError(
                request_info=None,  # type: ignore[arg-type]
                history=(),
                status=self.status,
            )

    async def json(self, content_type: Any = None) -> Any:
        return self._json


class FakeSession:
    """Captures requests and returns preset response(s).

    Accepts a single :class:`FakeResponse` or a list of them; successive calls
    return the next response, repeating the last once exhausted (handy for
    testing pagination). All POST bodies are recorded in ``posts``.
    """

    def __init__(self, response: FakeResponse | list[FakeResponse]) -> None:
        self._responses = response if isinstance(response, list) else [response]
        self._calls = 0
        self.last_url: str = ""
        self.last_method: str = ""
        self.last_headers: dict[str, str] = {}
        self.last_data: dict[str, str] = {}
        self.last_json: Any = None
        self.posts: list[Any] = []

    def _next(self) -> FakeResponse:
        response = self._responses[min(self._calls, len(self._responses) - 1)]
        self._calls += 1
        return response

    def post(
        self,
        url: str,
        *,
        data: dict[str, str] | None = None,
        json: Any = None,
        headers: dict[str, str] | None = None,
    ) -> FakeResponse:
        self.last_url = url
        self.last_method = "POST"
        self.last_data = data or {}
        self.last_json = json
        self.last_headers = headers or {}
        self.posts.append(json)
        return self._next()

    def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        allow_redirects: bool = True,
    ) -> FakeResponse:
        self.last_url = url
        self.last_method = "GET"
        self.last_headers = headers or {}
        return self._next()


class TimeoutSession(FakeSession):
    """A session whose requests raise TimeoutError."""

    def post(self, *args: Any, **kwargs: Any) -> FakeResponse:  # noqa: D401
        raise TimeoutError

    def get(self, *args: Any, **kwargs: Any) -> FakeResponse:
        raise TimeoutError


def fake_json_response(data: Any, status: int = 200) -> FakeResponse:
    return FakeResponse(status=status, json_data=data)


def fake_status_response(status: int) -> FakeResponse:
    return FakeResponse(status=status, json_data=None)
