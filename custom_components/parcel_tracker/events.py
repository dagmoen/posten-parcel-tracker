"""Pure event-diffing logic for the coordinator.

Given the previously seen state and the freshly fetched parcels, compute which
Home Assistant events should fire. Separated from the coordinator so it can be
unit tested without Home Assistant.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .const import (
    EVENT_DELIVERED,
    EVENT_NEW_PACKAGE,
    EVENT_READY_FOR_PICKUP,
    EVENT_STATUS_CHANGED,
)
from .models import Parcel, ParcelStatus


@dataclass(slots=True)
class FiredEvent:
    """A single event to emit on the HA bus."""

    event_type: str
    parcel: Parcel
    extra: dict = field(default_factory=dict)


@dataclass(slots=True)
class DiffResult:
    """Result of an event diff."""

    events: list[FiredEvent]
    last_status: dict[str, ParcelStatus]
    known_ids: set[str]


def diff_events(
    parcels: list[Parcel],
    *,
    previous_status: dict[str, ParcelStatus],
    known_ids: set[str],
    first_run: bool,
) -> DiffResult:
    """Return the events to fire plus the updated tracking state.

    On ``first_run`` no events are fired (avoids a startup burst), but state is
    still recorded.
    """
    events: list[FiredEvent] = []
    new_status = dict(previous_status)
    current_ids = {p.parcel_id for p in parcels}

    for parcel in parcels:
        pid = parcel.parcel_id
        previous = previous_status.get(pid)

        if not first_run and pid not in known_ids:
            events.append(FiredEvent(EVENT_NEW_PACKAGE, parcel))

        if not first_run and previous is not None and previous != parcel.status:
            events.append(
                FiredEvent(
                    EVENT_STATUS_CHANGED,
                    parcel,
                    {"previous_status": previous.value},
                )
            )
            if parcel.is_ready_for_pickup:
                events.append(FiredEvent(EVENT_READY_FOR_PICKUP, parcel))
            elif parcel.is_delivered:
                events.append(FiredEvent(EVENT_DELIVERED, parcel))

        new_status[pid] = parcel.status

    for stale in known_ids - current_ids:
        new_status.pop(stale, None)

    return DiffResult(events=events, last_status=new_status, known_ids=current_ids)
