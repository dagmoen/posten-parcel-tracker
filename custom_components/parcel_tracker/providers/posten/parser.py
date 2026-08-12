"""Parse raw Posten parcel JSON into normalized :class:`Parcel` objects.

The Posten parcel API is undocumented, so this parser is deliberately tolerant:
it looks for a set of known field names (observed in the app's data model) and
degrades gracefully when a field is missing or renamed. All parsing quirks stay
contained in this module.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from ...models import Parcel, ParcelEvent
from .const import CARRIER_NAME, TRACKING_URL_TEMPLATE
from .status import normalize_status


def _first(data: dict[str, Any], *keys: str) -> Any:
    """Return the first present, non-None value among ``keys``."""
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return None


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value or None
    return str(value)


def _parse_datetime(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        # Try a plain date.
        parsed = _parse_date(value)
        return datetime(parsed.year, parsed.month, parsed.day) if parsed else None


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, dict):
        value = _first(value, "date", "day", "value")
    if not isinstance(value, str):
        return None
    text = value.strip()
    for candidate in (text, text.split("T", 1)[0]):
        try:
            return date.fromisoformat(candidate)
        except ValueError:
            continue
    dt = _parse_datetime(value)
    return dt.date() if dt else None


def _sender_name(data: dict[str, Any]) -> str | None:
    sender = _first(data, "sender", "senderName", "shipper", "from")
    if isinstance(sender, dict):
        return _as_str(_first(sender, "name", "displayName", "senderName"))
    return _as_str(sender)


def _pickup_location(data: dict[str, Any]) -> str | None:
    for key in ("pickupPoint", "pickUpPoint", "favoritePickUpPoint", "location"):
        point = data.get(key)
        if isinstance(point, dict):
            name = _as_str(_first(point, "name", "locationName", "displayName"))
            if name:
                return name
        elif isinstance(point, str) and point:
            return point
    return None


def _expected_delivery(data: dict[str, Any]) -> date | None:
    for key in (
        "estimatedDeliveryDate",
        "expectedDelivery",
        "deliveryDate",
        "estimatedDeliveryTime",
        "estimatedDeliveryWindow",
        "deliveryWindow",
    ):
        value = data.get(key)
        parsed = _parse_date(value)
        if parsed:
            return parsed
    return None


def _parse_events(data: dict[str, Any]) -> list[ParcelEvent]:
    raw_events = _first(data, "events", "trackingEvents", "history")
    if not isinstance(raw_events, list):
        return []
    events: list[ParcelEvent] = []
    for item in raw_events:
        if not isinstance(item, dict):
            continue
        description = _as_str(
            _first(item, "description", "displayText", "text", "status", "name")
        )
        raw_status = _as_str(_first(item, "status", "phase", "type"))
        events.append(
            ParcelEvent(
                description=description,
                status=normalize_status(raw_status) if raw_status else None,
                time=_parse_datetime(
                    _first(item, "dateTime", "time", "timestamp", "date")
                ),
            )
        )
    return events


def parse_parcel(data: dict[str, Any]) -> Parcel | None:
    """Parse a single raw parcel dict. Returns ``None`` if unusable."""
    if not isinstance(data, dict):
        return None

    tracking_number = _as_str(
        _first(
            data,
            "parcelNumber",
            "trackingNumber",
            "consignmentNumber",
            "parcelItemNumber",
            "shipmentNumber",
            "id",
        )
    )
    parcel_id = tracking_number or _as_str(_first(data, "id", "key"))
    if not parcel_id:
        return None

    raw_status = _as_str(_first(data, "status", "displayStatus", "phase"))
    status = normalize_status(raw_status)

    name = _as_str(
        _first(data, "alias", "customName", "name", "parcelContent", "productName")
    )
    status_text = _as_str(_first(data, "displayStatus", "statusText", "statusDescription"))

    tracking_url = _as_str(_first(data, "trackingUrl", "url"))
    if not tracking_url and tracking_number:
        tracking_url = TRACKING_URL_TEMPLATE.format(parcel_id=tracking_number)

    return Parcel(
        parcel_id=parcel_id,
        status=status,
        raw_status=raw_status,
        carrier=CARRIER_NAME,
        tracking_number=tracking_number,
        sender=_sender_name(data),
        name=name,
        status_text=status_text or raw_status,
        expected_delivery=_expected_delivery(data),
        pickup_location=_pickup_location(data),
        tracking_url=tracking_url,
        direction=_as_str(_first(data, "direction")),
        events=_parse_events(data),
    )


def parse_parcels(payload: Any) -> list[Parcel]:
    """Parse the parcel-list response into normalized parcels.

    Accepts either a bare list, or an object wrapping the list under a common
    key (``parcels``/``items``/``parcelDataList``/``data``).
    """
    items: Any = payload
    if isinstance(payload, dict):
        items = _first(
            payload, "parcels", "items", "parcelDataList", "parcelList", "data", "result"
        )
    if not isinstance(items, list):
        return []

    parcels: list[Parcel] = []
    for item in items:
        parcel = parse_parcel(item)
        if parcel is not None:
            parcels.append(parcel)
    return parcels
