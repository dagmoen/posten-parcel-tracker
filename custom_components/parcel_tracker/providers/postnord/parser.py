"""Parse PostNord ``/api/user/shipments`` JSON into normalized parcels.

The response groups shipments as ``{"to": [...], "from": [...],
"archived": [...]}``. We keep the parcels the user is receiving (``is_consignee``)
so counts reflect incoming parcels, mirroring the Posten provider.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from ...models import Parcel, ParcelEvent, ParcelStatus
from .const import CARRIER_NAME
from .status import normalize_status


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_ddmmyyyy(value: Any) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.strptime(value.strip(), "%d.%m.%Y").date()
    except ValueError:
        return None


def _parse_dt(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def _delivery_type(data: dict[str, Any]) -> str | None:
    if data.get("is_parcel_locker"):
        return "parcel_locker_delivery"
    if _as_str(data.get("service_point")):
        return "pib_delivery"
    return None


def parse_shipment(data: dict[str, Any]) -> Parcel | None:
    """Parse a single shipment dict. Returns ``None`` if unusable."""
    if not isinstance(data, dict):
        return None
    parcel_id = _as_str(data.get("id"))
    if not parcel_id:
        return None

    raw_status = _as_str(data.get("status_status"))
    status = normalize_status(raw_status)
    # The explicit flag is the clearest "collectable" signal.
    if data.get("ready_for_pickup"):
        status = ParcelStatus.READY_FOR_PICKUP

    status_text = _as_str(data.get("status_text")) or _as_str(data.get("status_header"))
    updated = _parse_dt(data.get("updated_at")) or _parse_dt(data.get("created_at"))
    events = (
        [
            ParcelEvent(
                description=status_text,
                status=status,
                time=updated,
                location=_as_str(data.get("service_point")),
            )
        ]
        if status_text
        else []
    )

    return Parcel(
        parcel_id=parcel_id,
        status=status,
        raw_status=raw_status,
        carrier=CARRIER_NAME,
        tracking_number=parcel_id,
        sender=_as_str(data.get("consignor")),
        recipient_name=_as_str(data.get("consignee")),
        recipient_address=_as_str(data.get("consignee_street")),
        name=_as_str(data.get("name")),
        status_text=status_text,
        expected_delivery=_parse_ddmmyyyy(data.get("estimated_delivery_at")),
        delivery_type=_delivery_type(data),
        pickup_location=_as_str(data.get("service_point")),
        direction="receive",
        events=events,
    )


def parse_shipments(payload: Any) -> list[Parcel]:
    """Parse the grouped shipments response into incoming parcels."""
    if not isinstance(payload, dict):
        return []
    parcels: list[Parcel] = []
    seen: set[str] = set()
    for group in ("to", "archived", "from"):
        items = payload.get(group)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict) or not item.get("is_consignee"):
                continue  # keep only parcels the user is receiving
            parcel = parse_shipment(item)
            if parcel is not None and parcel.parcel_id not in seen:
                seen.add(parcel.parcel_id)
                parcels.append(parcel)
    return parcels
