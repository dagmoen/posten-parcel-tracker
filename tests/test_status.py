"""Tests for Posten status normalization."""

from __future__ import annotations

import pytest

from custom_components.parcel_tracker.models import ParcelStatus
from custom_components.parcel_tracker.providers.posten.status import normalize_status


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("PRE_NOTIFIED", ParcelStatus.REGISTERED),
        ("Pre Notified", ParcelStatus.REGISTERED),
        ("UNDERWAY", ParcelStatus.IN_TRANSIT),
        ("Underway", ParcelStatus.IN_TRANSIT),
        ("COLLECTABLE", ParcelStatus.READY_FOR_PICKUP),
        ("DELIVERED", ParcelStatus.DELIVERED),
        ("ARCHIVED", ParcelStatus.DELIVERED),
        ("PASSIVE_RETURN_UNDERWAY", ParcelStatus.RETURNED),
        ("PASSIVE_RETURN_COLLECTABLE", ParcelStatus.RETURNED),
        ("UNKNOWN", ParcelStatus.UNKNOWN),
    ],
)
def test_known_statuses(raw: str, expected: ParcelStatus) -> None:
    assert normalize_status(raw) is expected


@pytest.mark.parametrize("raw", [None, "", "   "])
def test_empty_returns_unknown(raw) -> None:
    assert normalize_status(raw) is ParcelStatus.UNKNOWN


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("out_for_delivery", ParcelStatus.OUT_FOR_DELIVERY),
        ("some-delay-happened", ParcelStatus.DELAYED),
        ("READY_FOR_PICKUP_AT_STORE", ParcelStatus.READY_FOR_PICKUP),
        ("in transit now", ParcelStatus.IN_TRANSIT),
        ("totally-made-up", ParcelStatus.UNKNOWN),
    ],
)
def test_heuristic_fallback(raw: str, expected: ParcelStatus) -> None:
    assert normalize_status(raw) is expected


def test_case_and_separator_insensitive() -> None:
    assert normalize_status("collectable") is ParcelStatus.READY_FOR_PICKUP
    assert normalize_status("pre-notified") is ParcelStatus.REGISTERED
