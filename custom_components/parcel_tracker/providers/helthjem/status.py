"""Map Helthjem statuses onto the normalized model.

Helthjem uses an UPPER_SNAKE status enum on both the parcel and its events
(seen: REGISTERED, IN_TRANSIT, DELIVERING). We normalize case-insensitively and
fall back sensibly for unseen values.
"""

from __future__ import annotations

from ...models import ParcelStatus

_STATUS_MAP: dict[str, ParcelStatus] = {
    "CREATED": ParcelStatus.REGISTERED,
    "REGISTERED": ParcelStatus.REGISTERED,
    "PRE_NOTIFIED": ParcelStatus.REGISTERED,
    "NOTIFIED": ParcelStatus.REGISTERED,
    "IN_TRANSIT": ParcelStatus.IN_TRANSIT,
    "SORTING": ParcelStatus.IN_TRANSIT,
    "ON_ROUTE": ParcelStatus.IN_TRANSIT,
    "DELIVERING": ParcelStatus.OUT_FOR_DELIVERY,
    "OUT_FOR_DELIVERY": ParcelStatus.OUT_FOR_DELIVERY,
    "READY_FOR_PICKUP": ParcelStatus.READY_FOR_PICKUP,
    "COLLECTABLE": ParcelStatus.READY_FOR_PICKUP,
    "DELIVERED": ParcelStatus.DELIVERED,
    "RETURNED": ParcelStatus.RETURNED,
    "CANCELLED": ParcelStatus.RETURNED,
}

# Human-readable Norwegian text per status, used for event descriptions since
# Helthjem's events carry only status codes (no readable text).
_STATUS_TEXT: dict[str, str] = {
    "CREATED": "Registrert",
    "REGISTERED": "Registrert",
    "PRE_NOTIFIED": "Varslet",
    "NOTIFIED": "Varslet",
    "IN_TRANSIT": "Underveis",
    "SORTING": "Sortering",
    "ON_ROUTE": "Underveis",
    "DELIVERING": "Ut for levering",
    "OUT_FOR_DELIVERY": "Ut for levering",
    "READY_FOR_PICKUP": "Klar for henting",
    "COLLECTABLE": "Klar for henting",
    "DELIVERED": "Levert",
    "RETURNED": "Returnert",
    "CANCELLED": "Kansellert",
}


def _key(raw: str) -> str:
    return raw.strip().upper().replace(" ", "_").replace("-", "_")


def normalize_status(raw: str | None) -> ParcelStatus:
    """Return the normalized status for a raw Helthjem status string."""
    if not raw:
        return ParcelStatus.UNKNOWN
    key = _key(raw)
    if key in _STATUS_MAP:
        return _STATUS_MAP[key]
    if "DELIVER" in key and "OUT" not in key and "DELIVERING" not in key:
        return ParcelStatus.DELIVERED
    if "DELIVER" in key:
        return ParcelStatus.OUT_FOR_DELIVERY
    if "RETURN" in key or "CANCEL" in key:
        return ParcelStatus.RETURNED
    if "PICK" in key or "COLLECT" in key:
        return ParcelStatus.READY_FOR_PICKUP
    if "TRANSIT" in key or "ROUTE" in key or "SORT" in key:
        return ParcelStatus.IN_TRANSIT
    if "CREATE" in key or "REGISTER" in key or "NOTIF" in key:
        return ParcelStatus.REGISTERED
    return ParcelStatus.UNKNOWN


def status_text(raw: str | None) -> str | None:
    """Return a Norwegian label for a raw status, for event descriptions."""
    if not raw:
        return None
    return _STATUS_TEXT.get(_key(raw), raw)
