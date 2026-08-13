"""Map PostNord shipment statuses onto the normalized model.

PostNord exposes a ``status_status`` machine value (e.g. ``CREATED``,
``EN_ROUTE``, ``DELIVERED``) plus a ``ready_for_pickup`` boolean. We normalize
case-insensitively and fall back sensibly for unseen values.
"""

from __future__ import annotations

from ...models import ParcelStatus

_STATUS_MAP: dict[str, ParcelStatus] = {
    "CREATED": ParcelStatus.REGISTERED,
    "PRE_NOTIFIED": ParcelStatus.REGISTERED,
    "NOTIFIED": ParcelStatus.REGISTERED,
    "REGISTERED": ParcelStatus.REGISTERED,
    "EN_ROUTE": ParcelStatus.IN_TRANSIT,
    "IN_TRANSIT": ParcelStatus.IN_TRANSIT,
    "SORTING": ParcelStatus.IN_TRANSIT,
    "OUT_FOR_DELIVERY": ParcelStatus.OUT_FOR_DELIVERY,
    "AVAILABLE_FOR_PICKUP": ParcelStatus.READY_FOR_PICKUP,
    "READY_FOR_PICKUP": ParcelStatus.READY_FOR_PICKUP,
    "COLLECTABLE": ParcelStatus.READY_FOR_PICKUP,
    "DELIVERED": ParcelStatus.DELIVERED,
    "RETURNED": ParcelStatus.RETURNED,
    "RETURN": ParcelStatus.RETURNED,
}


def normalize_status(raw: str | None) -> ParcelStatus:
    """Return the normalized status for a raw PostNord status string."""
    if not raw:
        return ParcelStatus.UNKNOWN

    key = raw.strip().upper().replace(" ", "_").replace("-", "_")
    if key in _STATUS_MAP:
        return _STATUS_MAP[key]

    if "DELIVER" in key and "OUT" in key:
        return ParcelStatus.OUT_FOR_DELIVERY
    if "DELIVER" in key:
        return ParcelStatus.DELIVERED
    if "RETURN" in key:
        return ParcelStatus.RETURNED
    if "PICK" in key or "COLLECT" in key:
        return ParcelStatus.READY_FOR_PICKUP
    if "ROUTE" in key or "TRANSIT" in key or "SORT" in key:
        return ParcelStatus.IN_TRANSIT
    if "CREATE" in key or "REGISTER" in key or "NOTIF" in key:
        return ParcelStatus.REGISTERED
    return ParcelStatus.UNKNOWN
