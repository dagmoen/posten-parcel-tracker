"""Tests for the Posten API client and end-to-end provider parsing."""

from __future__ import annotations

import pytest

from custom_components.parcel_tracker.models import ParcelStatus
from custom_components.parcel_tracker.providers import (
    AuthenticationError,
    ProviderTimeoutError,
)
from custom_components.parcel_tracker.providers.posten import PostenAuth, PostenProvider
from custom_components.parcel_tracker.providers.posten.client import PostenClient

from .fake_http import (
    FakeSession,
    TimeoutSession,
    fake_json_response,
    fake_status_response,
)


def _authed(session: FakeSession) -> PostenAuth:
    # Pre-seed a valid (non-expired) token so no refresh round-trip is needed.
    return PostenAuth(
        session,
        refresh_token="r",
        access_token="valid-token",
        expires_at=9_999_999_999,
    )


@pytest.mark.asyncio
async def test_client_posts_bearer_and_returns_json() -> None:
    session = FakeSession(fake_json_response({"parcels": []}))
    client = PostenClient(session, _authed(session))
    data = await client.async_get_parcels_raw()
    assert data == {"parcels": []}
    assert session.last_url.endswith("/parcel-api/v1/parcel")
    # The list endpoint is a POST with a JSON body (a GET returns HTTP 500).
    assert session.last_method == "POST"
    assert session.last_json["exclude"] == []
    assert "lastUpdated" in session.last_json
    assert session.last_headers["Authorization"] == "Bearer valid-token"
    assert session.last_headers["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_client_paginates_via_exclude() -> None:
    # Two pages: the first reports remainingCount > 0, the second clears it.
    session = FakeSession(
        [
            fake_json_response(
                {
                    "parcels": [{"parcelNumber": "P1"}, {"parcelNumber": "P2"}],
                    "totalCount": 3,
                    "remainingCount": 1,
                }
            ),
            fake_json_response(
                {"parcels": [{"parcelNumber": "P3"}], "remainingCount": 0}
            ),
        ]
    )
    client = PostenClient(session, _authed(session))
    data = await client.async_get_parcels_raw()
    assert [p["parcelNumber"] for p in data["parcels"]] == ["P1", "P2", "P3"]
    # Second request must exclude the parcels already fetched.
    assert len(session.posts) == 2
    assert session.posts[0]["exclude"] == []
    assert session.posts[1]["exclude"] == ["P1", "P2"]


@pytest.mark.asyncio
async def test_client_auth_failure() -> None:
    session = FakeSession(fake_status_response(401))
    client = PostenClient(session, _authed(session))
    with pytest.raises(AuthenticationError):
        await client.async_get_parcels_raw()


@pytest.mark.asyncio
async def test_client_timeout() -> None:
    session = TimeoutSession(fake_json_response({}))
    client = PostenClient(session, _authed(session))
    with pytest.raises(ProviderTimeoutError):
        await client.async_get_parcels_raw()


@pytest.mark.asyncio
async def test_provider_end_to_end_parsing() -> None:
    payload = {
        "parcels": [
            {
                "parcelNumber": "P1",
                "status": "COLLECTABLE",
                "sender": {"name": "IKEA"},
            },
            {"parcelNumber": "P2", "status": "DELIVERED"},
        ]
    }
    session = FakeSession(fake_json_response(payload))
    provider = PostenProvider(session, _authed(session))
    parcels = list(await provider.async_get_parcels())
    assert len(parcels) == 2
    by_id = {p.parcel_id: p for p in parcels}
    assert by_id["P1"].status is ParcelStatus.READY_FOR_PICKUP
    assert by_id["P1"].sender == "IKEA"
    assert by_id["P2"].status is ParcelStatus.DELIVERED
