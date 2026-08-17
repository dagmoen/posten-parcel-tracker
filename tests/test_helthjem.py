"""Tests for the Helthjem provider: status, parser, client, provider."""

from __future__ import annotations

from datetime import date

import pytest

from custom_components.parcel_tracker.models import ParcelStatus
from custom_components.parcel_tracker.providers import AuthenticationError
from custom_components.parcel_tracker.providers.helthjem import HelthjemProvider
from custom_components.parcel_tracker.providers.helthjem.client import HelthjemClient
from custom_components.parcel_tracker.providers.helthjem.parser import build_parcel
from custom_components.parcel_tracker.providers.helthjem.status import normalize_status

from .fake_http import FakeSession, fake_json_response


def _list_response() -> dict:
    return {
        "data": {
            "getUserPackages": {
                "pagination": {"total": 1},
                "data": [
                    {
                        "id": "1",
                        "trackingCode": "370724763519623838",
                        "userStatus": "RECEIVED",
                        "shop": None,
                        "orderData": {
                            "recipientAddress": {"city": "Oslo", "zipCode": "1169"}
                        },
                    }
                ],
            }
        }
    }


def _detail_response() -> dict:
    return {
        "data": {
            "getParcelTrackingDetails": {
                "parcelReference": "370724763519623838",
                "status": "DELIVERING",
                "estimatedDelivery": {"date": "2026-08-18T04:30:35+02:00"},
                "shop": {"name": "Komplett"},
                "servicePoint": None,
                "events": [
                    {
                        "createdAt": "2026-08-17T04:30:35+02:00",
                        "status": "DELIVERING",
                        "location": "OSLO",
                    },
                    {
                        "createdAt": "2026-08-15T10:00:00+02:00",
                        "status": "REGISTERED",
                        "location": None,
                    },
                ],
            }
        }
    }


def _user_response() -> dict:
    return {
        "data": {
            "getLoggedUser": {
                "recipientAddresses": [
                    {"city": "Oslo", "zipCode": "1169", "default": True}
                ]
            }
        }
    }


def test_status_normalization() -> None:
    assert normalize_status("DELIVERING") is ParcelStatus.OUT_FOR_DELIVERY
    assert normalize_status("IN_TRANSIT") is ParcelStatus.IN_TRANSIT
    assert normalize_status("REGISTERED") is ParcelStatus.REGISTERED
    assert normalize_status("DELIVERED") is ParcelStatus.DELIVERED
    assert normalize_status(None) is ParcelStatus.UNKNOWN


def test_build_parcel_merges_list_and_detail() -> None:
    item = _list_response()["data"]["getUserPackages"]["data"][0]
    detail = _detail_response()["data"]["getParcelTrackingDetails"]
    parcel = build_parcel(item, detail)
    assert parcel is not None
    assert parcel.tracking_number == "370724763519623838"
    assert parcel.status is ParcelStatus.OUT_FOR_DELIVERY
    assert parcel.is_active
    assert parcel.sender == "Komplett"  # from detail even though list shop was null
    assert parcel.carrier == "Helthjem"
    assert parcel.expected_delivery == date(2026, 8, 18)
    assert parcel.recipient_city == "Oslo"
    assert parcel.direction == "receive"
    # No service point -> home delivery ("leveres hjem").
    assert parcel.delivery_type == "home_delivery"


def test_build_parcel_uses_default_recipient_when_missing() -> None:
    item = {"id": "9", "trackingCode": "TC9", "userStatus": "RECEIVED", "orderData": None}
    parcel = build_parcel(item, None, {"city": "Bergen", "zipCode": "5000"})
    assert parcel is not None
    assert parcel.recipient_city == "Bergen"
    assert parcel.recipient_postal_code == "5000"


def test_build_parcel_pickup_point() -> None:
    item = _list_response()["data"]["getUserPackages"]["data"][0]
    detail = _detail_response()["data"]["getParcelTrackingDetails"]
    detail = {**detail, "servicePoint": {"name": "Joker Ljan", "address": "Ljansv 1"}}
    parcel = build_parcel(item, detail)
    assert parcel is not None
    assert parcel.delivery_type == "pib_delivery"
    assert parcel.pickup_location == "Joker Ljan"
    assert len(parcel.events) == 2
    assert parcel.events[0].description == "Ut for levering"
    assert parcel.events[0].location == "OSLO"


@pytest.mark.asyncio
async def test_client_auth_error_on_unauthenticated() -> None:
    session = FakeSession(
        fake_json_response({"errors": [{"message": "UNAUTHENTICATED: token expired"}]})
    )
    client = HelthjemClient(session, "session_token=stale")
    with pytest.raises(AuthenticationError):
        await client.async_get_packages()


@pytest.mark.asyncio
async def test_provider_end_to_end() -> None:
    # POST order: list -> getLoggedUser -> detail.
    session = FakeSession(
        [
            fake_json_response(_list_response()),
            fake_json_response(_user_response()),
            fake_json_response(_detail_response()),
        ]
    )
    provider = HelthjemProvider(session, "session_token=abc")
    parcels = list(await provider.async_get_parcels())
    assert len(parcels) == 1
    parcel = parcels[0]
    assert parcel.sender == "Komplett"
    assert parcel.status is ParcelStatus.OUT_FOR_DELIVERY
    assert parcel.expected_delivery == date(2026, 8, 18)
    # The GraphQL request carried the session cookie.
    assert session.last_headers["Cookie"] == "session_token=abc"
