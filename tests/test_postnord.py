"""Tests for the PostNord provider: status, parser, and client."""

from __future__ import annotations

from datetime import date

import pytest

from custom_components.parcel_tracker.models import ParcelStatus
from custom_components.parcel_tracker.providers import (
    AuthenticationError,
    ProviderTimeoutError,
)
from custom_components.parcel_tracker.providers.postnord.client import PostNordClient
from custom_components.parcel_tracker.providers.postnord.parser import parse_shipments
from custom_components.parcel_tracker.providers.postnord.status import normalize_status

from .fake_http import FakeSession, TimeoutSession, fake_json_response, fake_status_response


def _payload() -> dict:
    # Mirrors the live app.postnord.no /api/user/shipments shape.
    return {
        "to": [
            {
                "id": "70581500471419279",
                "consignor": "Torrfisk.no",
                "consignee": "Dag Moen",
                "consignee_street": "Ljansbakken 17",
                "service_point": "PAKKEAUTOMAT LJAN STASJON",
                "estimated_delivery_at": "18.08.2026",
                "status_status": "EN_ROUTE",
                "status_header": "Underveis",
                "status_text": "Vi har sendt pakken fra TROMSO",
                "ready_for_pickup": False,
                "is_parcel_locker": True,
                "is_consignee": True,
                "created_at": "2026-08-12 10:02",
                "updated_at": "2026-08-13 13:55",
            }
        ],
        "from": [
            {
                "id": "70733748533702155",
                "consignor": "Dag Moen",
                "consignee": "Sport Holding",
                "status_status": "CREATED",
                "is_consignee": False,  # outgoing -> excluded
            }
        ],
        "archived": [
            {
                "id": "70733748533702131",
                "consignor": "Sport Holding as",
                "consignee": "Dag Moen",
                "consignee_street": "Ljansbakken 17",
                "service_point": "JOKER LJAN",
                "status_status": "DELIVERED",
                "status_header": "Levert",
                "status_text": "Pakken din er levert",
                "ready_for_pickup": False,
                "is_parcel_locker": False,
                "is_consignee": True,
                "updated_at": "2026-08-12 14:13",
            }
        ],
    }


def test_status_normalization() -> None:
    assert normalize_status("CREATED") is ParcelStatus.REGISTERED
    assert normalize_status("EN_ROUTE") is ParcelStatus.IN_TRANSIT
    assert normalize_status("DELIVERED") is ParcelStatus.DELIVERED
    assert normalize_status("AVAILABLE_FOR_PICKUP") is ParcelStatus.READY_FOR_PICKUP
    assert normalize_status(None) is ParcelStatus.UNKNOWN


def test_parse_keeps_incoming_only() -> None:
    parcels = parse_shipments(_payload())
    # "from" entry (is_consignee False) is excluded.
    ids = {p.parcel_id for p in parcels}
    assert ids == {"70581500471419279", "70733748533702131"}


def test_parse_active_parcel_fields() -> None:
    parcels = parse_shipments(_payload())
    active = next(p for p in parcels if p.parcel_id == "70581500471419279")
    assert active.status is ParcelStatus.IN_TRANSIT
    assert active.is_active
    assert active.sender == "Torrfisk.no"
    assert active.recipient_name == "Dag Moen"
    assert active.recipient_address == "Ljansbakken 17"
    assert active.carrier == "PostNord"
    assert active.tracking_number == "70581500471419279"
    assert active.expected_delivery == date(2026, 8, 18)
    assert active.delivery_type == "parcel_locker_delivery"
    assert active.pickup_location == "PAKKEAUTOMAT LJAN STASJON"
    assert active.direction == "receive"
    assert active.events and active.events[0].description


def test_parse_delivered_parcel() -> None:
    parcels = parse_shipments(_payload())
    delivered = next(p for p in parcels if p.parcel_id == "70733748533702131")
    assert delivered.status is ParcelStatus.DELIVERED
    assert delivered.is_delivered
    assert delivered.delivery_type == "pib_delivery"


def test_ready_for_pickup_flag_overrides_status() -> None:
    payload = {
        "to": [
            {
                "id": "X1",
                "consignor": "Shop",
                "consignee": "Me",
                "status_status": "EN_ROUTE",
                "ready_for_pickup": True,
                "is_consignee": True,
            }
        ]
    }
    parcel = parse_shipments(payload)[0]
    assert parcel.status is ParcelStatus.READY_FOR_PICKUP


@pytest.mark.asyncio
async def test_client_returns_json() -> None:
    session = FakeSession(fake_json_response(_payload()))
    client = PostNordClient(session, "session=abc")
    data = await client.async_get_shipments_raw()
    assert set(data.keys()) == {"to", "from", "archived"}
    assert session.last_url.endswith("/api/user/shipments")
    assert session.last_headers["Cookie"] == "session=abc"


@pytest.mark.asyncio
async def test_client_expired_cookie_raises_auth() -> None:
    # A login redirect (302) means the cookie is no longer valid.
    session = FakeSession(fake_status_response(302))
    client = PostNordClient(session, "session=stale")
    with pytest.raises(AuthenticationError):
        await client.async_get_shipments_raw()


@pytest.mark.asyncio
async def test_client_timeout() -> None:
    session = TimeoutSession(fake_json_response({}))
    client = PostNordClient(session, "session=abc")
    with pytest.raises(ProviderTimeoutError):
        await client.async_get_shipments_raw()
