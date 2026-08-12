"""Provider abstraction for the Parcel Tracker integration.

A provider knows how to authenticate against a carrier and how to fetch the
user's parcels as normalized :class:`~custom_components.parcel_tracker.models.Parcel`
objects. Keeping this layer free of Home Assistant imports makes providers easy
to unit test in isolation.
"""

from __future__ import annotations

import abc
from collections.abc import Sequence

from ..models import Parcel


class ProviderError(Exception):
    """Base error for all provider failures."""


class AuthenticationError(ProviderError):
    """Raised when authentication fails or the session has expired."""


class ProviderTimeoutError(ProviderError):
    """Raised when a request to the provider times out."""


class ProviderConnectionError(ProviderError):
    """Raised for network/connection level failures."""


class Provider(abc.ABC):
    """Abstract base every carrier provider implements."""

    #: Stable machine identifier, e.g. ``"posten"``.
    provider_id: str
    #: Human-readable carrier name used as the parcel ``carrier`` field.
    carrier_name: str

    @abc.abstractmethod
    async def async_get_parcels(self) -> Sequence[Parcel]:
        """Return all parcels currently associated with the account."""

    async def async_close(self) -> None:
        """Release any resources held by the provider. Optional override."""
