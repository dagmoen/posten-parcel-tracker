"""HTTP client for the PostNord account shipments endpoint."""

from __future__ import annotations

import aiohttp
import async_timeout

from .. import (
    AuthenticationError,
    ProviderConnectionError,
    ProviderTimeoutError,
)
from .const import API_BASE, REQUEST_TIMEOUT, SHIPMENTS_PATH, USER_AGENT


class PostNordClient:
    """Fetches the account shipment list using the web session cookie."""

    def __init__(self, session: aiohttp.ClientSession, cookie: str) -> None:
        self._session = session
        self._cookie = cookie

    async def async_get_shipments_raw(self) -> dict:
        """Return the raw shipments JSON (``{to, from, archived}``).

        Auth is the PostNord web session cookie. An expired/invalid cookie makes
        the endpoint redirect to login, which we treat as an auth failure so
        Home Assistant can prompt for a fresh cookie.
        """
        url = f"{API_BASE}{SHIPMENTS_PATH}"
        headers = {
            "Cookie": self._cookie,
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        }
        try:
            async with async_timeout.timeout(REQUEST_TIMEOUT):
                # Don't follow redirects: a login redirect means the cookie is
                # no longer valid.
                async with self._session.get(
                    url, headers=headers, allow_redirects=False
                ) as resp:
                    if resp.status in (301, 302, 303, 307, 308, 401, 403):
                        raise AuthenticationError(
                            f"PostNord session cookie rejected (HTTP {resp.status})"
                        )
                    resp.raise_for_status()
                    try:
                        return await resp.json(content_type=None)
                    except (aiohttp.ContentTypeError, ValueError) as err:
                        # Non-JSON (e.g. an HTML login page) means the cookie is
                        # no longer accepted.
                        raise AuthenticationError(
                            "PostNord returned a non-JSON response; the session "
                            "cookie is likely expired"
                        ) from err
        except AuthenticationError:
            raise
        except TimeoutError as err:
            raise ProviderTimeoutError("Timed out talking to app.postnord.no") from err
        except aiohttp.ClientError as err:
            raise ProviderConnectionError(str(err)) from err
