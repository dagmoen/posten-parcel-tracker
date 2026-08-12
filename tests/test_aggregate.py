"""Tests for the pure aggregation logic that drives sensor states."""

from __future__ import annotations

from datetime import date, datetime, timezone

from custom_components.parcel_tracker import aggregate
from custom_components.parcel_tracker.models import Parcel, ParcelEvent, ParcelStatus

TODAY = date(2026, 8, 12)


def _p(pid: str, status: ParcelStatus, expected: date | None = None) -> Parcel:
    return Parcel(
        parcel_id=pid,
        status=status,
        raw_status=status.value,
        expected_delivery=expected,
    )


def _parcels() -> list[Parcel]:
    return [
        _p("a", ParcelStatus.IN_TRANSIT, TODAY),
        _p("b", ParcelStatus.READY_FOR_PICKUP),
        _p("c", ParcelStatus.DELIVERED),
        _p("d", ParcelStatus.REGISTERED, date(2026, 8, 20)),
        _p("e", ParcelStatus.OUT_FOR_DELIVERY, date(2026, 8, 13)),
        _p("f", ParcelStatus.RETURNED),
    ]


def test_active_excludes_delivered_and_returned() -> None:
    active = aggregate.active_parcels(_parcels())
    assert {p.parcel_id for p in active} == {"a", "b", "d", "e"}


def test_delivered_and_ready_and_arriving_today() -> None:
    parcels = _parcels()
    assert {p.parcel_id for p in aggregate.delivered_parcels(parcels)} == {"c"}
    assert {p.parcel_id for p in aggregate.ready_for_pickup_parcels(parcels)} == {"b"}
    arriving = aggregate.arriving_today_parcels(parcels, TODAY)
    assert {p.parcel_id for p in arriving} == {"a"}


def test_next_delivery_is_earliest_active_dated() -> None:
    nxt = aggregate.next_delivery_parcel(_parcels())
    assert nxt is not None
    assert nxt.parcel_id == "a"  # 2026-08-12 beats 08-13 and 08-20


def test_next_delivery_none_when_no_dates() -> None:
    parcels = [_p("x", ParcelStatus.IN_TRANSIT), _p("y", ParcelStatus.READY_FOR_PICKUP)]
    assert aggregate.next_delivery_parcel(parcels) is None


def test_retention_hides_delivered_when_disabled() -> None:
    parcels = _parcels()
    kept = aggregate.apply_retention(
        parcels, today=TODAY, retention_days=7, show_delivered=False
    )
    assert all(not p.is_delivered for p in kept)
    assert {p.parcel_id for p in kept} == {"a", "b", "d", "e", "f"}


def test_retention_drops_old_delivered() -> None:
    old = Parcel(
        parcel_id="old",
        status=ParcelStatus.DELIVERED,
        events=[
            ParcelEvent(
                description="Delivered",
                time=datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc),
            )
        ],
    )
    recent = Parcel(
        parcel_id="recent",
        status=ParcelStatus.DELIVERED,
        events=[
            ParcelEvent(
                description="Delivered",
                time=datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc),
            )
        ],
    )
    kept = aggregate.apply_retention(
        [old, recent], today=TODAY, retention_days=7, show_delivered=True
    )
    # cutoff = 2026-08-05; old (08-01) dropped, recent (08-11) kept.
    assert {p.parcel_id for p in kept} == {"recent"}
