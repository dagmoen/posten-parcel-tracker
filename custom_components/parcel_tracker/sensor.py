"""Sensor platform for the Parcel Tracker integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_ENABLE_PACKAGE_ENTITIES,
    DEFAULT_ENABLE_PACKAGE_ENTITIES,
    DOMAIN,
)
from .coordinator import ParcelData, ParcelUpdateCoordinator
from .models import Parcel
from .serialize import parcel_to_dict


@dataclass(frozen=True, kw_only=True)
class ParcelSensorDescription(SensorEntityDescription):
    """Describes an aggregate parcel sensor."""

    value_fn: Callable[[ParcelData], int | date | None]
    attributes_fn: Callable[[ParcelData], dict] | None = None


def _next_delivery_value(data: ParcelData) -> date | None:
    parcel = data.next_delivery
    return parcel.expected_delivery if parcel else None


def _next_delivery_attributes(data: ParcelData) -> dict:
    parcel = data.next_delivery
    return parcel_to_dict(parcel) if parcel else {}


def _active_attributes(data: ParcelData) -> dict:
    return {"packages": [parcel_to_dict(p) for p in data.active]}


SENSOR_DESCRIPTIONS: tuple[ParcelSensorDescription, ...] = (
    ParcelSensorDescription(
        key="active",
        translation_key="active",
        icon="mdi:package-variant-closed",
        native_unit_of_measurement="parcels",
        state_class="measurement",
        value_fn=lambda data: len(data.active),
        attributes_fn=_active_attributes,
    ),
    ParcelSensorDescription(
        key="arriving_today",
        translation_key="arriving_today",
        icon="mdi:truck-delivery-outline",
        native_unit_of_measurement="parcels",
        state_class="measurement",
        value_fn=lambda data: len(data.arriving_today),
    ),
    ParcelSensorDescription(
        key="next_delivery",
        translation_key="next_delivery",
        icon="mdi:calendar-clock",
        device_class=SensorDeviceClass.DATE,
        value_fn=_next_delivery_value,
        attributes_fn=_next_delivery_attributes,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up parcel sensors from a config entry."""
    coordinator: ParcelUpdateCoordinator = entry.runtime_data

    entities: list[SensorEntity] = [
        ParcelAggregateSensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    ]

    if entry.options.get(
        CONF_ENABLE_PACKAGE_ENTITIES, DEFAULT_ENABLE_PACKAGE_ENTITIES
    ):
        known: set[str] = set()

        @callback
        def _add_new_parcels() -> None:
            # Only create per-package entities for incoming (active) parcels, so
            # the dashboard isn't cluttered with delivered/archived items.
            new_entities: list[SensorEntity] = []
            for parcel in coordinator.data.parcels:
                if not parcel.is_active or parcel.parcel_id in known:
                    continue
                known.add(parcel.parcel_id)
                new_entities.append(
                    ParcelPackageSensor(coordinator, entry, parcel.parcel_id)
                )
            if new_entities:
                async_add_entities(new_entities)

        _add_new_parcels()
        entry.async_on_unload(coordinator.async_add_listener(_add_new_parcels))

    async_add_entities(entities)


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title or "Parcel Tracker",
        manufacturer="Posten/Bring",
        entry_type=DeviceEntryType.SERVICE,
    )


class ParcelAggregateSensor(
    CoordinatorEntity[ParcelUpdateCoordinator], SensorEntity
):
    """An aggregate sensor (counts, next delivery)."""

    entity_description: ParcelSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ParcelUpdateCoordinator,
        entry: ConfigEntry,
        description: ParcelSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> int | date | None:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict | None:
        if self.entity_description.attributes_fn is None:
            return None
        return self.entity_description.attributes_fn(self.coordinator.data)


class ParcelPackageSensor(
    CoordinatorEntity[ParcelUpdateCoordinator], SensorEntity
):
    """One sensor per incoming parcel; state is the normalized status."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:package"

    def __init__(
        self,
        coordinator: ParcelUpdateCoordinator,
        entry: ConfigEntry,
        parcel_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._parcel_id = parcel_id
        self._attr_unique_id = f"{entry.entry_id}_parcel_{parcel_id}"
        self._attr_device_info = _device_info(entry)

    @property
    def _parcel(self) -> Parcel | None:
        for parcel in self.coordinator.data.parcels:
            if parcel.parcel_id == self._parcel_id:
                return parcel
        return None

    @property
    def available(self) -> bool:
        return super().available and self._parcel is not None

    @property
    def name(self) -> str:
        parcel = self._parcel
        if parcel and parcel.sender:
            return parcel.sender
        return f"Parcel {self._parcel_id}"

    @property
    def native_value(self) -> str | None:
        parcel = self._parcel
        return parcel.status.value if parcel else None

    @property
    def extra_state_attributes(self) -> dict | None:
        parcel = self._parcel
        return parcel_to_dict(parcel) if parcel else None
