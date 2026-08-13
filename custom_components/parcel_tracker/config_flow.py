"""Config and options flow for the Parcel Tracker integration."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_DELIVERED_RETENTION_DAYS,
    CONF_ENABLE_PACKAGE_ENTITIES,
    CONF_PROVIDER,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_INTERVAL_MINUTES,
    CONF_SHOW_DELIVERED,
    CONF_TOKEN_EXPIRES_AT,
    DEFAULT_DELIVERED_RETENTION_DAYS,
    DEFAULT_ENABLE_PACKAGE_ENTITIES,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DEFAULT_SHOW_DELIVERED,
    DOMAIN,
    MIN_SCAN_INTERVAL_MINUTES,
    PROVIDER_POSTEN,
)
from .providers import AuthenticationError, ProviderError
from .providers.posten.auth import PostenAuth, build_authorize_url, extract_code

CONF_AUTH_CODE = "auth_code"


class ParcelTrackerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the Posten OAuth login as a config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._state = uuid.uuid4().hex
        self._authorize_url = build_authorize_url(self._state)
        self._reauth_entry: ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the login URL and capture the pasted authorization code."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                code = extract_code(user_input[CONF_AUTH_CODE])
                session = async_get_clientsession(self.hass)
                auth = PostenAuth(session)
                token = await auth.async_exchange_code(code)
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except ProviderError:
                errors["base"] = "cannot_connect"
            else:
                data = {
                    CONF_PROVIDER: PROVIDER_POSTEN,
                    CONF_REFRESH_TOKEN: token.refresh_token,
                    CONF_ACCESS_TOKEN: token.access_token,
                    CONF_TOKEN_EXPIRES_AT: token.expires_at,
                }
                if self._reauth_entry is not None:
                    return self.async_update_reload_and_abort(
                        self._reauth_entry, data=data
                    )
                await self.async_set_unique_id(PROVIDER_POSTEN)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Parcel Tracker", data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_AUTH_CODE): str}),
            errors=errors,
            description_placeholders={"authorize_url": self._authorize_url},
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication when the token becomes invalid."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_user()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return ParcelTrackerOptionsFlow()


class ParcelTrackerOptionsFlow(OptionsFlow):
    """Options: polling interval, retention, delivered visibility, entities."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL_MINUTES,
                    default=options.get(
                        CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL_MINUTES)),
                vol.Required(
                    CONF_DELIVERED_RETENTION_DAYS,
                    default=options.get(
                        CONF_DELIVERED_RETENTION_DAYS,
                        DEFAULT_DELIVERED_RETENTION_DAYS,
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=90)),
                vol.Required(
                    CONF_SHOW_DELIVERED,
                    default=options.get(CONF_SHOW_DELIVERED, DEFAULT_SHOW_DELIVERED),
                ): bool,
                vol.Required(
                    CONF_ENABLE_PACKAGE_ENTITIES,
                    default=options.get(
                        CONF_ENABLE_PACKAGE_ENTITIES,
                        DEFAULT_ENABLE_PACKAGE_ENTITIES,
                    ),
                ): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
