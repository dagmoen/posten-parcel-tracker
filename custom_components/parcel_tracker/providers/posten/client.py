"""HTTP client for the Posten parcel API."""

from __future__ import annotations

import aiohttp
import async_timeout

from .. import (
    AuthenticationError,
    ProviderConnectionError,
    ProviderTimeoutError,
)
from .auth import PostenAuth
from .const import (
    API_BASE,
    PARCEL_LIST_PATH,
    PARCEL_SERVICE,
    REQUEST_TIMEOUT,
    USER_AGENT,
)


class PostenClient:
    """Thin wrapper over the api.posten.no parcel endpoints."""

    def __init__(self, session: aiohttp.ClientSession, auth: PostenAuth) -> None:
        self._session = session
        self._auth = auth

    async def async_get_parcels_raw(self) -> object:
        """Fetch the raw parcel-list JSON for the authenticated account.

        The parcel-list endpoint is a POST (a GET returns HTTP 500). The JSON
        body is a ``ParcelsRequest`` used by the app for delta sync; sending an
        empty body returns all parcels on the account, which is what we want.
        """
        access_token = await self._auth.async_valid_access_token()
        url = f"{API_BASE}{PARCEL_SERVICE}/{PARCEL_LIST_PATH}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        try:
            async with async_timeout.timeout(REQUEST_TIMEOUT):
                async with self._session.post(url, headers=headers, json={}) as resp:
                    if resp.status in (401, 403):
                        raise AuthenticationError(
                            f"Parcel request unauthorized (HTTP {resp.status})"
                        )
                    resp.raise_for_status()
                    return await resp.json(content_type=None)
        except AuthenticationError:
            raise
        except TimeoutError as err:
            raise ProviderTimeoutError("Timed out talking to api.posten.no") from err
        except aiohttp.ClientError as err:
            raise ProviderConnectionError(str(err)) from err
