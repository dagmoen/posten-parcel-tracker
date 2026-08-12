"""Constants for the Parcel Tracker integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "parcel_tracker"

# Config entry data keys
CONF_PROVIDER = "provider"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_ACCESS_TOKEN = "access_token"
CONF_TOKEN_EXPIRES_AT = "token_expires_at"

# Options keys
CONF_SCAN_INTERVAL_MINUTES = "scan_interval_minutes"
CONF_DELIVERED_RETENTION_DAYS = "delivered_retention_days"
CONF_SHOW_DELIVERED = "show_delivered"
CONF_ENABLE_PACKAGE_ENTITIES = "enable_package_entities"

# Option defaults
DEFAULT_SCAN_INTERVAL_MINUTES = 15
MIN_SCAN_INTERVAL_MINUTES = 5
DEFAULT_DELIVERED_RETENTION_DAYS = 7
DEFAULT_SHOW_DELIVERED = True
DEFAULT_ENABLE_PACKAGE_ENTITIES = True

DEFAULT_SCAN_INTERVAL = timedelta(minutes=DEFAULT_SCAN_INTERVAL_MINUTES)

# Providers
PROVIDER_POSTEN = "posten"
DEFAULT_PROVIDER = PROVIDER_POSTEN

# Events
EVENT_NEW_PACKAGE = f"{DOMAIN}_new_package"
EVENT_STATUS_CHANGED = f"{DOMAIN}_status_changed"
EVENT_READY_FOR_PICKUP = f"{DOMAIN}_ready_for_pickup"
EVENT_DELIVERED = f"{DOMAIN}_delivered"
