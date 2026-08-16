"""DataUpdateCoordinator for the Parcel Tracker integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta

import homeassistant.util.dt as dt_util
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from . import aggregate
from .const import (
    CONF_DELIVERED_RETENTION_DAYS,
    CONF_SCAN_INTERVAL_MINUTES,
    CONF_SHOW_DELIVERED,
    DEFAULT_DELIVERED_RETENTION_DAYS,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DEFAULT_SHOW_DELIVERED,
    DOMAIN,
    MIN_SCAN_INTERVAL_MINUTES,
)
from .events import diff_events
from .models import Parcel, ParcelStatus
from .providers import (
    AuthenticationError,
    Provider,
    ProviderConnectionError,
    ProviderError,
    ProviderTimeoutError,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ParcelData:
    """Computed snapshot exposed to entities."""

    parcels: list[Parcel] = field(default_factory=list)

    @property
    def active(self) -> list[Parcel]:
        return aggregate.active_parcels(self.parcels)

    @property
    def delivered(self) -> list[Parcel]:
        return aggregate.delivered_parcels(self.parcels)

    @property
    def ready_for_pickup(self) -> list[Parcel]:
        return aggregate.ready_for_pickup_parcels(self.parcels)

    @property
    def arriving_today(self) -> list[Parcel]:
        return aggregate.arriving_today_parcels(self.parcels, dt_util.now().date())

    @property
    def next_delivery(self) -> Parcel | None:
        """Earliest active parcel with a known expected delivery date."""
        return aggregate.next_delivery_parcel(self.parcels)


class ParcelUpdateCoordinator(DataUpdateCoordinator[ParcelData]):
    """Coordinates a single shared refresh for all entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        provider: Provider,
    ) -> None:
        self.entry = entry
        self.provider = provider
        # Snapshot of options so the update listener can tell an options change
        # (needs a reload) from a token-data update (must not reload).
        self.current_options = dict(entry.options)
        # Snapshot of last-seen status per parcel id, for event firing.
        self._last_status: dict[str, ParcelStatus] = {}
        self._known_ids: set[str] = set()
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=self._interval,
        )

    @property
    def _interval(self) -> timedelta:
        minutes = self.entry.options.get(
            CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES
        )
        minutes = max(int(minutes), MIN_SCAN_INTERVAL_MINUTES)
        return timedelta(minutes=minutes)

    async def _async_update_data(self) -> ParcelData:
        try:
            parcels = list(await self.provider.async_get_parcels())
        except AuthenticationError as err:
            # Trigger re-auth flow in Home Assistant.
            from homeassistant.exceptions import ConfigEntryAuthFailed

            raise ConfigEntryAuthFailed(str(err)) from err
        except (ProviderTimeoutError, ProviderConnectionError) as err:
            raise UpdateFailed(f"Could not reach provider: {err}") from err
        except ProviderError as err:
            raise UpdateFailed(str(err)) from err

        parcels = self._apply_retention(parcels)
        self._fire_events(parcels)
        return ParcelData(parcels=parcels)

    def _apply_retention(self, parcels: list[Parcel]) -> list[Parcel]:
        """Drop old delivered parcels and optionally hide delivered ones."""
        retention_days = int(
            self.entry.options.get(
                CONF_DELIVERED_RETENTION_DAYS, DEFAULT_DELIVERED_RETENTION_DAYS
            )
        )
        show_delivered = self.entry.options.get(
            CONF_SHOW_DELIVERED, DEFAULT_SHOW_DELIVERED
        )
        return aggregate.apply_retention(
            parcels,
            today=dt_util.now().date(),
            retention_days=retention_days,
            show_delivered=show_delivered,
        )

    def _fire_events(self, parcels: list[Parcel]) -> None:
        """Fire HA events for new packages and status transitions."""
        # Skip the very first refresh to avoid a burst of events on startup.
        first_run = not self._known_ids and not self._last_status

        result = diff_events(
            parcels,
            previous_status=self._last_status,
            known_ids=self._known_ids,
            first_run=first_run,
        )
        for fired in result.events:
            self._bus_fire(fired.event_type, fired.parcel, fired.extra)

        self._last_status = result.last_status
        self._known_ids = result.known_ids

    def _bus_fire(
        self, event_type: str, parcel: Parcel, extra: dict | None = None
    ) -> None:
        data = {
            "entry_id": self.entry.entry_id,
            "parcel_id": parcel.parcel_id,
            "tracking_number": parcel.tracking_number,
            "carrier": parcel.carrier,
            "status": parcel.status.value,
            "status_text": parcel.status_text,
            "sender": parcel.sender,
            "name": parcel.name,
            "delivery_type": parcel.delivery_type,
            "delivery_method": parcel.delivery_type_label,
            "pickup_location": parcel.pickup_location,
        }
        if extra:
            data.update(extra)
        self.hass.bus.async_fire(event_type, data)
