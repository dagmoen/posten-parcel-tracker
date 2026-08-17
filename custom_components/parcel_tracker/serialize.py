"""Pure serialization of :class:`Parcel` to plain dicts.

Kept free of Home Assistant imports so it can be unit tested and reused by both
the sensor attributes and the dashboard-friendly ``packages`` list.
"""

from __future__ import annotations

from datetime import date, datetime

from .models import Parcel

# Norwegian display labels baked into the attributes so dashboard cards don't
# have to maintain their own lookup tables. This integration only supports
# Norwegian carriers, so Norwegian labels are appropriate here.
_STATUS_NB: dict[str, str] = {
    "registered": "Registrert",
    "in_transit": "Underveis",
    "out_for_delivery": "Ut for levering",
    "ready_for_pickup": "Klar for henting",
    "delivered": "Levert",
    "delayed": "Forsinket",
    "returned": "Returnert",
    "unknown": "Ukjent",
}
_DELIVERY_NB: dict[str, str] = {
    "home_delivery": "Hjemlevering",
    "mailbox_delivery": "Postkasse",
    "pib_delivery": "Hentested",
    "parcel_locker_delivery": "Pakkeboks",
    "parcel_robot_delivery": "Leveringsrobot",
    "personal_delivery": "Personlig levering",
}
_CARRIER_DOT: dict[str, str] = {
    "Posten/Bring": "🔴",
    "PostNord": "🔵",
    "Helthjem": "🟡",
}


def _iso(value: date | datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def parcel_to_dict(parcel: Parcel) -> dict:
    """Serialize a parcel to a flat dict for entity attributes / dashboards."""
    latest = parcel.latest_event
    return {
        "parcel_id": parcel.parcel_id,
        # Norwegian terms the app uses, for clarity on the dashboard.
        "kollinummer": parcel.tracking_number,
        "sendingsnummer": parcel.consignment_number,
        "sender": parcel.sender,
        "recipient": parcel.recipient_name,
        "recipient_address": parcel.recipient_address,
        "recipient_postal_code": parcel.recipient_postal_code,
        "recipient_city": parcel.recipient_city,
        "status": parcel.status.value,
        "status_text": parcel.status_text,
        # Ready-to-display Norwegian labels (so cards need no lookup tables).
        "status_label": _STATUS_NB.get(parcel.status.value, parcel.status.value),
        "delivery_label": _DELIVERY_NB.get(
            parcel.delivery_type or "", parcel.delivery_type_label
        ),
        "carrier_dot": _CARRIER_DOT.get(parcel.carrier, "⚪"),
        "delivery_method": parcel.delivery_type_label,
        "delivery_type": parcel.delivery_type,
        "expected_delivery": _iso(parcel.expected_delivery),
        "delivery_window_start": _iso(parcel.delivery_window_start),
        "delivery_window_end": _iso(parcel.delivery_window_end),
        "on_track": parcel.on_track,
        "weight_kg": parcel.weight_kg,
        "dimensions": parcel.dimensions_cm,
        "transport": parcel.transport_type,
        "carrier": parcel.carrier,
        "tracking_url": parcel.tracking_url,
        "latest_event": latest.description if latest else None,
        "latest_event_time": _iso(latest.time) if latest else None,
        "tracking": [
            {
                "time": _iso(event.time),
                "description": event.description,
                "location": event.location,
            }
            for event in parcel.events
        ],
    }
