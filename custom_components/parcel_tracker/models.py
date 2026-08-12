"""Provider-agnostic data models for parcels.

These models are the normalized representation used by the Home Assistant
platform code. Provider-specific parsing lives in each provider package and is
responsible for producing :class:`Parcel` instances.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum


class ParcelStatus(str, Enum):
    """Normalized parcel status shared across all providers.

    Inheriting from ``str`` keeps the values JSON-serializable and easy to use
    directly in Home Assistant attributes.
    """

    UNKNOWN = "unknown"
    REGISTERED = "registered"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    READY_FOR_PICKUP = "ready_for_pickup"
    DELIVERED = "delivered"
    DELAYED = "delayed"
    RETURNED = "returned"


# Statuses that represent a parcel that is still "in the system" and worth
# counting as active (i.e. not finished and not returned).
ACTIVE_STATUSES: frozenset[ParcelStatus] = frozenset(
    {
        ParcelStatus.REGISTERED,
        ParcelStatus.IN_TRANSIT,
        ParcelStatus.OUT_FOR_DELIVERY,
        ParcelStatus.READY_FOR_PICKUP,
        ParcelStatus.DELAYED,
    }
)


@dataclass(slots=True)
class ParcelEvent:
    """A single tracking event in a parcel's history."""

    description: str | None = None
    status: ParcelStatus | None = None
    time: datetime | None = None


@dataclass(slots=True)
class Parcel:
    """Normalized parcel model.

    ``raw_status`` preserves the untouched provider status so nothing is lost in
    normalization and troubleshooting stays possible.
    """

    parcel_id: str
    status: ParcelStatus
    raw_status: str | None = None
    carrier: str = "unknown"
    tracking_number: str | None = None
    sender: str | None = None
    name: str | None = None
    status_text: str | None = None
    expected_delivery: date | None = None
    pickup_location: str | None = None
    tracking_url: str | None = None
    direction: str | None = None
    events: list[ParcelEvent] = field(default_factory=list)

    @property
    def latest_event(self) -> ParcelEvent | None:
        """Return the most recent event, if any."""
        if not self.events:
            return None
        dated = [e for e in self.events if e.time is not None]
        if dated:
            return max(dated, key=lambda e: e.time)  # type: ignore[arg-type,return-value]
        return self.events[0]

    @property
    def is_active(self) -> bool:
        """Whether the parcel is still in progress."""
        return self.status in ACTIVE_STATUSES

    @property
    def is_delivered(self) -> bool:
        """Whether the parcel has been delivered."""
        return self.status is ParcelStatus.DELIVERED

    @property
    def is_ready_for_pickup(self) -> bool:
        """Whether the parcel is ready for pickup."""
        return self.status is ParcelStatus.READY_FOR_PICKUP
