"""Pure aggregation helpers over a list of parcels.

Kept free of Home Assistant imports so the counting/selection logic — which
drives every sensor's state — can be unit tested deterministically by injecting
``today``.
"""

from __future__ import annotations

from datetime import date, timedelta

from .models import Parcel


def active_parcels(parcels: list[Parcel]) -> list[Parcel]:
    return [p for p in parcels if p.is_active]


def delivered_parcels(parcels: list[Parcel]) -> list[Parcel]:
    return [p for p in parcels if p.is_delivered]


def ready_for_pickup_parcels(parcels: list[Parcel]) -> list[Parcel]:
    return [p for p in parcels if p.is_ready_for_pickup]


def arriving_today_parcels(parcels: list[Parcel], today: date) -> list[Parcel]:
    return [
        p for p in parcels if p.is_active and p.expected_delivery == today
    ]


def next_delivery_parcel(parcels: list[Parcel]) -> Parcel | None:
    """Earliest active parcel with a known expected delivery date."""
    dated = [p for p in parcels if p.is_active and p.expected_delivery is not None]
    if not dated:
        return None
    return min(dated, key=lambda p: p.expected_delivery)  # type: ignore[arg-type,return-value]


def apply_retention(
    parcels: list[Parcel],
    *,
    today: date,
    retention_days: int,
    show_delivered: bool,
) -> list[Parcel]:
    """Filter delivered parcels by retention window / visibility option."""
    cutoff = today - timedelta(days=retention_days)
    result: list[Parcel] = []
    for parcel in parcels:
        if parcel.is_delivered:
            if not show_delivered:
                continue
            latest = parcel.latest_event
            event_date = latest.time.date() if latest and latest.time else None
            if event_date is not None and event_date < cutoff:
                continue
        result.append(parcel)
    return result
