"""Tests for the Posten OAuth auth module (code parsing, exchange, refresh)."""

from __future__ import annotations

import base64

import pytest

from custom_components.parcel_tracker.providers import AuthenticationError
from custom_components.parcel_tracker.providers.posten import auth as auth_mod
from custom_components.parcel_tracker.providers.posten.auth import (
    PostenAuth,
    build_authorize_url,
    extract_code,
)
from custom_components.parcel_tracker.providers.posten.const import (
    CLIENT_ID,
    CLIENT_SECRET,
)

from .fake_http import FakeSession, fake_json_response, fake_status_response


def test_build_authorize_url_contains_client_and_redirect() -> None:
    url = build_authorize_url("state123")
    assert url.startswith("https://id.posten.no/api/oauth/authorizations/new?")
    assert f"client_id={CLIENT_ID}" in url
    assert "redirect_uri=posten%3A%2F%2Flogin" in url
    assert "state=state123" in url


@pytest.mark.parametrize(
    ("pasted", "expected"),
    [
        ("ABC123", "ABC123"),
        ("posten://login?code=XYZ789&state=s", "XYZ789"),
        ("posten://login?state=s&code=QQ", "QQ"),
        ("  spaced  ", "spaced"),
    ],
)
def test_extract_code(pasted: str, expected: str) -> None:
    assert extract_code(pasted) == expected


@pytest.mark.parametrize("bad", ["", "   ", "posten://login?state=only"])
def test_extract_code_rejects_bad_input(bad: str) -> None:
    with pytest.raises(AuthenticationError):
        extract_code(bad)


def test_basic_auth_header_encoding() -> None:
    header = auth_mod._basic_auth_header()
    assert header.startswith("Basic ")
    decoded = base64.b64decode(header.split(" ", 1)[1]).decode()
    assert decoded == f"{CLIENT_ID}:{CLIENT_SECRET}"


@pytest.mark.asyncio
async def test_exchange_code_success() -> None:
    session = FakeSession(
        fake_json_response(
            {
                "access_token": "acc",
                "refresh_token": "ref",
                "token_type": "Bearer",
                "expires_in": 3600,
            }
        )
    )
    auth = PostenAuth(session)
    token = await auth.async_exchange_code("code")
    assert token.access_token == "acc"
    assert token.refresh_token == "ref"
    assert not token.is_expired
    # Sends Basic auth to the token endpoint.
    assert session.last_url.endswith("/api/oauth/accesstoken")
    assert session.last_headers["Authorization"].startswith("Basic ")


@pytest.mark.asyncio
async def test_refresh_uses_refresh_grant() -> None:
    session = FakeSession(
        fake_json_response(
            {"access_token": "new", "refresh_token": "ref2", "expires_in": 100}
        )
    )
    auth = PostenAuth(session, refresh_token="old-refresh")
    token = await auth.async_refresh()
    assert token.access_token == "new"
    assert session.last_data["grant_type"] == "refresh_token"
    assert session.last_data["refresh_token"] == "old-refresh"


@pytest.mark.asyncio
async def test_exchange_code_auth_failure() -> None:
    session = FakeSession(fake_status_response(400))
    auth = PostenAuth(session)
    with pytest.raises(AuthenticationError):
        await auth.async_exchange_code("bad-code")


@pytest.mark.asyncio
async def test_valid_access_token_refreshes_when_expired() -> None:
    session = FakeSession(
        fake_json_response(
            {"access_token": "fresh", "refresh_token": "r", "expires_in": 3600}
        )
    )
    # expires_at=0 -> expired -> should refresh.
    auth = PostenAuth(session, refresh_token="r", access_token="stale", expires_at=0)
    token = await auth.async_valid_access_token()
    assert token == "fresh"


@pytest.mark.asyncio
async def test_missing_tokens_raise() -> None:
    session = FakeSession(fake_json_response({"access_token": "only"}))
    auth = PostenAuth(session)
    with pytest.raises(AuthenticationError):
        await auth.async_exchange_code("code")
