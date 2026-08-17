"""Build normalized parcels from Helthjem list + detail GraphQL data."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from ...models import Parcel, ParcelEvent
from .const import CARRIER_NAME
from .status import normalize_status, status_text


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_dt(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _parse_date(value: Any) -> date | None:
    dt = _parse_dt(value)
    if dt:
        return dt.date()
    if isinstance(value, str) and len(value) >= 10:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _parse_events(detail: dict[str, Any]) -> list[ParcelEvent]:
    raw_events = detail.get("events")
    if not isinstance(raw_events, list):
        return []
    events: list[ParcelEvent] = []
    for item in raw_events:
        if not isinstance(item, dict):
            continue
        raw = _as_str(item.get("status"))
        events.append(
            ParcelEvent(
                description=status_text(raw),
                status=normalize_status(raw) if raw else None,
                time=_parse_dt(item.get("createdAt")),
                location=_as_str(item.get("location")),
            )
        )
    return events


def build_parcel(
    item: dict[str, Any],
    detail: dict[str, Any] | None,
    default_recipient: dict[str, Any] | None = None,
) -> Parcel | None:
    """Combine a list item and its (optional) detail into a Parcel."""
    if not isinstance(item, dict):
        return None
    tracking = _as_str(item.get("trackingCode")) or _as_str(item.get("id"))
    if not tracking:
        return None

    detail = detail if isinstance(detail, dict) else {}
    raw_status = _as_str(detail.get("status")) or _as_str(item.get("userStatus"))
    status = normalize_status(raw_status)

    shop = detail.get("shop") or item.get("shop") or {}
    service_point = detail.get("servicePoint") or {}
    estimated = detail.get("estimatedDelivery") or {}
    recipient = (
        (item.get("orderData") or {}).get("recipientAddress")
        or default_recipient
        or {}
    )

    pickup_location = (
        _as_str(service_point.get("name")) if isinstance(service_point, dict) else None
    )
    # Helthjem doesn't expose a delivery-method field; it's a pickup point if a
    # service point is set, otherwise home delivery (the common case).
    delivery_type = "pib_delivery" if pickup_location else "home_delivery"

    return Parcel(
        parcel_id=tracking,
        status=status,
        raw_status=raw_status,
        carrier=CARRIER_NAME,
        tracking_number=tracking,
        sender=_as_str(shop.get("name")) if isinstance(shop, dict) else None,
        recipient_postal_code=_as_str(recipient.get("zipCode")),
        recipient_city=_as_str(recipient.get("city")),
        status_text=status_text(raw_status),
        expected_delivery=_parse_date(estimated.get("date"))
        if isinstance(estimated, dict)
        else None,
        delivery_type=delivery_type,
        pickup_location=pickup_location,
        direction="receive",
        events=_parse_events(detail),
    )
