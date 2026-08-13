"""PostNord provider implementation (cookie-authenticated web API)."""

from __future__ import annotations

from collections.abc import Sequence

import aiohttp

from ...const import PROVIDER_POSTNORD
from ...models import Parcel
from .. import Provider
from .client import PostNordClient
from .const import CARRIER_NAME
from .parser import parse_shipments


class PostNordProvider(Provider):
    """Fetch a user's parcels from the PostNord account web API."""

    provider_id = PROVIDER_POSTNORD
    carrier_name = CARRIER_NAME

    def __init__(self, session: aiohttp.ClientSession, cookie: str) -> None:
        self._client = PostNordClient(session, cookie)

    async def async_get_parcels(self) -> Sequence[Parcel]:
        raw = await self._client.async_get_shipments_raw()
        return parse_shipments(raw)


__all__ = ["PostNordProvider"]
