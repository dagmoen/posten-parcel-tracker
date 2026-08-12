"""Posten/Bring provider implementation."""

from __future__ import annotations

from collections.abc import Sequence

import aiohttp

from ...const import PROVIDER_POSTEN
from ...models import Parcel
from .. import Provider
from .auth import PostenAuth
from .client import PostenClient
from .const import CARRIER_NAME
from .parser import parse_parcels


class PostenProvider(Provider):
    """Fetch a user's parcels from the (unofficial) Posten account API."""

    provider_id = PROVIDER_POSTEN
    carrier_name = CARRIER_NAME

    def __init__(self, session: aiohttp.ClientSession, auth: PostenAuth) -> None:
        self._auth = auth
        self._client = PostenClient(session, auth)

    @property
    def auth(self) -> PostenAuth:
        return self._auth

    async def async_get_parcels(self) -> Sequence[Parcel]:
        raw = await self._client.async_get_parcels_raw()
        return parse_parcels(raw)


__all__ = ["PostenProvider", "PostenAuth"]
