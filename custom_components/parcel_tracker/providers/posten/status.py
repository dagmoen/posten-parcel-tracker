"""Map Posten-specific parcel statuses onto the normalized model.

The Posten app exposes a top-level parcel status enum with these values
(observed in the app): ``PRE_NOTIFIED``, ``UNDERWAY``, ``COLLECTABLE``,
``DELIVERED``, ``ARCHIVED``, ``PASSIVE_RETURN_UNDERWAY``,
``PASSIVE_RETURN_COLLECTABLE``, ``UNKNOWN``. The API may also surface finer
event-level phase strings, so we normalize case-insensitively and fall back
sensibly.
"""

from __future__ import annotations

from ...models import ParcelStatus

# Exact matches against the app's known status vocabulary (upper-cased keys).
_STATUS_MAP: dict[str, ParcelStatus] = {
    "PRE_NOTIFIED": ParcelStatus.REGISTERED,
    "PRENOTIFIED": ParcelStatus.REGISTERED,
    "REGISTERED": ParcelStatus.REGISTERED,
    "CREATED": ParcelStatus.REGISTERED,
    "UNDERWAY": ParcelStatus.IN_TRANSIT,
    "IN_TRANSIT": ParcelStatus.IN_TRANSIT,
    "ON_ITS_WAY": ParcelStatus.IN_TRANSIT,
    "OUT_FOR_DELIVERY": ParcelStatus.OUT_FOR_DELIVERY,
    "COLLECTABLE": ParcelStatus.READY_FOR_PICKUP,
    "READY_FOR_PICKUP": ParcelStatus.READY_FOR_PICKUP,
    "AVAILABLE_FOR_PICKUP": ParcelStatus.READY_FOR_PICKUP,
    "DELIVERED": ParcelStatus.DELIVERED,
    "DELAYED": ParcelStatus.DELAYED,
    "PASSIVE_RETURN_UNDERWAY": ParcelStatus.RETURNED,
    "PASSIVE_RETURN_COLLECTABLE": ParcelStatus.RETURNED,
    "RETURNED": ParcelStatus.RETURNED,
    "RETURN": ParcelStatus.RETURNED,
    # ARCHIVED is a UI-level state; treat as delivered/finished unless a more
    # specific status is present.
    "ARCHIVED": ParcelStatus.DELIVERED,
    "UNKNOWN": ParcelStatus.UNKNOWN,
}


def normalize_status(raw: str | None) -> ParcelStatus:
    """Return the normalized status for a raw Posten status string."""
    if not raw:
        return ParcelStatus.UNKNOWN

    key = raw.strip().upper().replace(" ", "_").replace("-", "_")
    if key in _STATUS_MAP:
        return _STATUS_MAP[key]

    # Heuristic fallbacks for unseen phase strings.
    if "DELIVER" in key and "OUT" in key:
        return ParcelStatus.OUT_FOR_DELIVERY
    if "DELIVER" in key:
        return ParcelStatus.DELIVERED
    if "RETURN" in key:
        return ParcelStatus.RETURNED
    if "COLLECT" in key or "PICKUP" in key or "PICK_UP" in key:
        return ParcelStatus.READY_FOR_PICKUP
    if "DELAY" in key:
        return ParcelStatus.DELAYED
    if "TRANSIT" in key or "UNDERWAY" in key or "SORT" in key:
        return ParcelStatus.IN_TRANSIT
    if "REGISTER" in key or "NOTIF" in key or "CREATED" in key:
        return ParcelStatus.REGISTERED
    return ParcelStatus.UNKNOWN
