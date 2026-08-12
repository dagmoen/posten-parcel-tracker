"""Tests for the normalized parcel model helpers (feed entity state)."""

from __future__ import annotations

from datetime import datetime, timezone

from custom_components.parcel_tracker.models import (
    ACTIVE_STATUSES,
    Parcel,
    ParcelEvent,
    ParcelStatus,
)


def test_status_flags() -> None:
    assert Parcel("a", ParcelStatus.IN_TRANSIT).is_active
    assert not Parcel("a", ParcelStatus.DELIVERED).is_active
    assert Parcel("a", ParcelStatus.DELIVERED).is_delivered
    assert Parcel("a", ParcelStatus.READY_FOR_PICKUP).is_ready_for_pickup


def test_active_statuses_membership() -> None:
    assert ParcelStatus.DELIVERED not in ACTIVE_STATUSES
    assert ParcelStatus.RETURNED not in ACTIVE_STATUSES
    assert ParcelStatus.IN_TRANSIT in ACTIVE_STATUSES


def test_latest_event_prefers_most_recent_dated() -> None:
    parcel = Parcel(
        "a",
        ParcelStatus.IN_TRANSIT,
        events=[
            ParcelEvent("early", time=datetime(2026, 1, 1, tzinfo=timezone.utc)),
            ParcelEvent("late", time=datetime(2026, 2, 1, tzinfo=timezone.utc)),
        ],
    )
    assert parcel.latest_event is not None
    assert parcel.latest_event.description == "late"


def test_latest_event_falls_back_to_first_when_undated() -> None:
    parcel = Parcel(
        "a",
        ParcelStatus.IN_TRANSIT,
        events=[ParcelEvent("only")],
    )
    assert parcel.latest_event is not None
    assert parcel.latest_event.description == "only"


def test_latest_event_none_when_empty() -> None:
    assert Parcel("a", ParcelStatus.IN_TRANSIT).latest_event is None


def test_status_is_json_serializable_value() -> None:
    # str-based enum keeps a plain string value for HA attributes.
    assert ParcelStatus.READY_FOR_PICKUP.value == "ready_for_pickup"
    assert ParcelStatus.IN_TRANSIT == "in_transit"
