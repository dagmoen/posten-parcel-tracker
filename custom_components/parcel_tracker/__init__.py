"""The Parcel Tracker integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_DELIVERED_RETENTION_DAYS,
    CONF_PROVIDER,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN_EXPIRES_AT,
    DEFAULT_DELIVERED_RETENTION_DAYS,
    DEFAULT_PROVIDER,
    DOMAIN,
    PROVIDER_POSTEN,
)
from .coordinator import ParcelUpdateCoordinator
from .providers import Provider
from .providers.posten import PostenAuth, PostenProvider
from .providers.posten.const import PARCEL_LOOKBACK_DAYS

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

ParcelConfigEntry = ConfigEntry[ParcelUpdateCoordinator]


def _build_provider(hass: HomeAssistant, entry: ConfigEntry) -> Provider:
    """Instantiate the provider selected in the config entry."""
    provider_id = entry.data.get(CONF_PROVIDER, DEFAULT_PROVIDER)
    session = async_get_clientsession(hass)

    if provider_id == PROVIDER_POSTEN:
        auth = PostenAuth(
            session,
            refresh_token=entry.data.get(CONF_REFRESH_TOKEN),
            access_token=entry.data.get(CONF_ACCESS_TOKEN),
            expires_at=entry.data.get(CONF_TOKEN_EXPIRES_AT, 0.0),
        )
        # Fetch a window wide enough to cover both active parcels and any
        # delivered ones still within the user's retention setting.
        retention = int(
            entry.options.get(
                CONF_DELIVERED_RETENTION_DAYS, DEFAULT_DELIVERED_RETENTION_DAYS
            )
        )
        lookback_days = max(PARCEL_LOOKBACK_DAYS, retention + 7)
        return PostenProvider(session, auth, lookback_days=lookback_days)

    raise ValueError(f"Unknown provider: {provider_id}")


async def async_setup_entry(hass: HomeAssistant, entry: ParcelConfigEntry) -> bool:
    """Set up Parcel Tracker from a config entry."""
    provider = _build_provider(hass, entry)
    coordinator = ParcelUpdateCoordinator(hass, entry, provider)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ParcelConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        coordinator = entry.runtime_data
        await coordinator.provider.async_close()
    return unloaded


async def _async_update_listener(
    hass: HomeAssistant, entry: ParcelConfigEntry
) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
