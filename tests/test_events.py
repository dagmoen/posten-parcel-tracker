"""Tests for the pure coordinator event-diffing logic."""

from __future__ import annotations

from custom_components.parcel_tracker.const import (
    EVENT_DELIVERED,
    EVENT_NEW_PACKAGE,
    EVENT_READY_FOR_PICKUP,
    EVENT_STATUS_CHANGED,
)
from custom_components.parcel_tracker.events import diff_events
from custom_components.parcel_tracker.models import Parcel, ParcelStatus


def _p(pid: str, status: ParcelStatus) -> Parcel:
    return Parcel(parcel_id=pid, status=status, raw_status=status.value)


def test_first_run_fires_nothing_but_records_state() -> None:
    parcels = [_p("a", ParcelStatus.IN_TRANSIT)]
    result = diff_events(
        parcels, previous_status={}, known_ids=set(), first_run=True
    )
    assert result.events == []
    assert result.known_ids == {"a"}
    assert result.last_status == {"a": ParcelStatus.IN_TRANSIT}


def test_new_package_event() -> None:
    result = diff_events(
        [_p("a", ParcelStatus.IN_TRANSIT), _p("b", ParcelStatus.REGISTERED)],
        previous_status={"a": ParcelStatus.IN_TRANSIT},
        known_ids={"a"},
        first_run=False,
    )
    types = [e.event_type for e in result.events]
    assert EVENT_NEW_PACKAGE in types
    new = next(e for e in result.events if e.event_type == EVENT_NEW_PACKAGE)
    assert new.parcel.parcel_id == "b"


def test_status_change_to_ready_for_pickup() -> None:
    result = diff_events(
        [_p("a", ParcelStatus.READY_FOR_PICKUP)],
        previous_status={"a": ParcelStatus.IN_TRANSIT},
        known_ids={"a"},
        first_run=False,
    )
    types = [e.event_type for e in result.events]
    assert EVENT_STATUS_CHANGED in types
    assert EVENT_READY_FOR_PICKUP in types
    changed = next(e for e in result.events if e.event_type == EVENT_STATUS_CHANGED)
    assert changed.extra["previous_status"] == ParcelStatus.IN_TRANSIT.value


def test_status_change_to_delivered() -> None:
    result = diff_events(
        [_p("a", ParcelStatus.DELIVERED)],
        previous_status={"a": ParcelStatus.OUT_FOR_DELIVERY},
        known_ids={"a"},
        first_run=False,
    )
    types = [e.event_type for e in result.events]
    assert EVENT_DELIVERED in types


def test_no_change_no_events() -> None:
    result = diff_events(
        [_p("a", ParcelStatus.IN_TRANSIT)],
        previous_status={"a": ParcelStatus.IN_TRANSIT},
        known_ids={"a"},
        first_run=False,
    )
    assert result.events == []


def test_removed_parcel_forgotten() -> None:
    result = diff_events(
        [_p("a", ParcelStatus.IN_TRANSIT)],
        previous_status={"a": ParcelStatus.IN_TRANSIT, "gone": ParcelStatus.DELIVERED},
        known_ids={"a", "gone"},
        first_run=False,
    )
    assert "gone" not in result.last_status
    assert result.known_ids == {"a"}
