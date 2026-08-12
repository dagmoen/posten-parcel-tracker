"""Diagnostics support for Parcel Tracker (with secret redaction)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_ACCESS_TOKEN, CONF_REFRESH_TOKEN, CONF_TOKEN_EXPIRES_AT
from .coordinator import ParcelUpdateCoordinator

TO_REDACT = {
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN_EXPIRES_AT,
    "tracking_number",
    "sender",
    "pickup_location",
    "tracking_url",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return redacted diagnostics for a config entry."""
    coordinator: ParcelUpdateCoordinator = entry.runtime_data
    data = coordinator.data

    parcels = [
        {
            "status": p.status.value,
            "raw_status": p.raw_status,
            "carrier": p.carrier,
            "direction": p.direction,
            "has_expected_delivery": p.expected_delivery is not None,
            "event_count": len(p.events),
        }
        for p in (data.parcels if data else [])
    ]

    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "summary": {
            "total": len(parcels),
            "active": len(data.active) if data else 0,
            "delivered": len(data.delivered) if data else 0,
            "ready_for_pickup": len(data.ready_for_pickup) if data else 0,
        },
        "parcels": parcels,
    }
