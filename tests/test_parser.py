"""Tests for parsing raw Posten parcel JSON into normalized parcels."""

from __future__ import annotations

from datetime import date

from custom_components.parcel_tracker.models import ParcelStatus
from custom_components.parcel_tracker.providers.posten.parser import (
    parse_parcel,
    parse_parcels,
)


def _sample() -> dict:
    return {
        "parcelNumber": "TESTTRACK123",
        "status": "COLLECTABLE",
        "displayStatus": "Ready at pickup point",
        "alias": "Headphones",
        "direction": "receive",
        "sender": {"name": "Elkjøp"},
        "estimatedDeliveryDate": "2026-08-14",
        "pickupPoint": {"name": "Rema 1000 Majorstuen"},
        "events": [
            {
                "description": "Registered",
                "status": "PRE_NOTIFIED",
                "dateTime": "2026-08-11T09:00:00Z",
            },
            {
                "description": "Ready for pickup",
                "status": "COLLECTABLE",
                "dateTime": "2026-08-13T14:30:00Z",
            },
        ],
    }


def test_parse_full_parcel() -> None:
    parcel = parse_parcel(_sample())
    assert parcel is not None
    assert parcel.tracking_number == "TESTTRACK123"
    assert parcel.parcel_id == "TESTTRACK123"
    assert parcel.status is ParcelStatus.READY_FOR_PICKUP
    assert parcel.raw_status == "COLLECTABLE"
    assert parcel.name == "Headphones"
    assert parcel.sender == "Elkjøp"
    assert parcel.carrier == "Posten/Bring"
    assert parcel.expected_delivery == date(2026, 8, 14)
    assert parcel.pickup_location == "Rema 1000 Majorstuen"
    assert parcel.tracking_url and "TESTTRACK123" in parcel.tracking_url
    assert parcel.direction == "receive"


def test_latest_event_is_most_recent() -> None:
    parcel = parse_parcel(_sample())
    assert parcel is not None
    latest = parcel.latest_event
    assert latest is not None
    assert latest.description == "Ready for pickup"


def test_parse_is_tolerant_of_missing_fields() -> None:
    parcel = parse_parcel({"parcelNumber": "X1", "status": "UNDERWAY"})
    assert parcel is not None
    assert parcel.status is ParcelStatus.IN_TRANSIT
    assert parcel.sender is None
    assert parcel.expected_delivery is None
    assert parcel.events == []


def test_parse_without_identifier_returns_none() -> None:
    assert parse_parcel({"status": "UNDERWAY"}) is None
    assert parse_parcel("not a dict") is None  # type: ignore[arg-type]


def test_parse_parcels_from_list() -> None:
    parcels = parse_parcels([_sample(), {"parcelNumber": "Y2", "status": "DELIVERED"}])
    assert len(parcels) == 2
    assert {p.parcel_id for p in parcels} == {"TESTTRACK123", "Y2"}


def test_parse_parcels_from_wrapped_object() -> None:
    payload = {"parcels": [_sample()]}
    parcels = parse_parcels(payload)
    assert len(parcels) == 1


def test_parse_parcels_handles_garbage() -> None:
    assert parse_parcels(None) == []
    assert parse_parcels({"unexpected": "shape"}) == []
    # Bad entries are skipped, good ones kept.
    parcels = parse_parcels([{"bad": True}, {"parcelNumber": "Z", "status": "DELIVERED"}])
    assert len(parcels) == 1


def _real_response() -> dict:
    """Shape mirrors the live POST /parcel-api/v1/parcel response (2026-08-13)."""
    return {
        "parcels": [
            {
                "parcelNumber": "370722152135687874",
                "consignmentNumber": "70722152135231588",
                "status": "archived",
                "direction": "receive",
                "sender": {"name": "Dun of Norway AS"},
                "productName": "new_norway_bring_pickup_parcel",
                "delivery": {
                    "pickUpPointId": "121573",
                    "shelfNumber": "W5",
                    "type": "pib_delivery",
                },
                "events": [
                    {
                        "description": "The parcel has been delivered.",
                        "date": "2025-09-18T11:35:49Z",
                        "type": "delivered",
                        "displayStatus": "significant",
                    },
                    {
                        "description": "The parcel has arrived at Matkroken Ljabru.",
                        "date": "2025-09-18T09:51:26Z",
                        "type": "ready_for_pick_up",
                        "displayStatus": "significant",
                    },
                ],
            }
        ]
    }


def test_parse_real_response_shape() -> None:
    parcels = parse_parcels(_real_response())
    assert len(parcels) == 1
    parcel = parcels[0]
    assert parcel.parcel_id == "370722152135687874"
    assert parcel.tracking_number == "370722152135687874"
    # Lowercase "archived" normalizes to DELIVERED.
    assert parcel.status is ParcelStatus.DELIVERED
    assert parcel.raw_status == "archived"
    assert parcel.sender == "Dun of Norway AS"
    assert parcel.carrier == "Posten/Bring"
    assert parcel.direction == "receive"
    # Event "type" drives per-event status; latest (delivered) wins.
    event_statuses = {e.status for e in parcel.events}
    assert ParcelStatus.DELIVERED in event_statuses
    assert ParcelStatus.READY_FOR_PICKUP in event_statuses
    assert parcel.latest_event is not None
    assert parcel.latest_event.status is ParcelStatus.DELIVERED


def test_alternate_field_names() -> None:
    parcel = parse_parcel(
        {
            "consignmentNumber": "C-99",
            "displayStatus": "Delivered",
            "shipper": {"senderName": "Zalando"},
            "deliveryDate": "2026-08-10T00:00:00Z",
        }
    )
    assert parcel is not None
    assert parcel.tracking_number == "C-99"
    assert parcel.status is ParcelStatus.DELIVERED
    assert parcel.sender == "Zalando"
    assert parcel.expected_delivery == date(2026, 8, 10)
