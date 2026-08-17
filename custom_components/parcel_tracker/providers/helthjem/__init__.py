"""Helthjem provider implementation (cookie-authenticated GraphQL API)."""

from __future__ import annotations

from collections.abc import Sequence

import aiohttp

from ...const import PROVIDER_HELTHJEM
from ...models import Parcel
from .. import Provider, ProviderConnectionError, ProviderTimeoutError
from .client import HelthjemClient
from .const import CARRIER_NAME
from .parser import build_parcel


class HelthjemProvider(Provider):
    """Fetch a user's parcels from the Helthjem account GraphQL API.

    Two-step: list the user's packages, then enrich each with its rich tracking
    detail (status, estimated delivery, sender, pickup point, events).
    """

    provider_id = PROVIDER_HELTHJEM
    carrier_name = CARRIER_NAME

    def __init__(self, session: aiohttp.ClientSession, cookie: str) -> None:
        self._client = HelthjemClient(session, cookie)

    async def async_get_parcels(self) -> Sequence[Parcel]:
        items = await self._client.async_get_packages()
        parcels: list[Parcel] = []
        for item in items:
            reference = item.get("trackingCode") if isinstance(item, dict) else None
            detail = None
            if reference:
                try:
                    detail = await self._client.async_get_details(reference)
                except (ProviderTimeoutError, ProviderConnectionError):
                    # A single flaky detail call shouldn't drop the parcel; fall
                    # back to the thinner list data. Auth errors still propagate.
                    detail = None
            parcel = build_parcel(item, detail)
            if parcel is not None:
                parcels.append(parcel)
        return parcels


__all__ = ["HelthjemProvider"]
