"""GraphQL client for the Helthjem account API."""

from __future__ import annotations

from typing import Any

import aiohttp
import async_timeout

from .. import (
    AuthenticationError,
    ProviderConnectionError,
    ProviderError,
    ProviderTimeoutError,
)
from .const import (
    API_URL,
    DETAIL_QUERY,
    INCOMING_TYPES,
    LIST_PAGE_SIZE,
    LIST_QUERY,
    REQUEST_TIMEOUT,
    USER_AGENT,
    USER_QUERY,
)


class HelthjemClient:
    """Talks to services.helthjem.no/graphql using the web session cookie."""

    def __init__(self, session: aiohttp.ClientSession, cookie: str) -> None:
        self._session = session
        self._cookie = cookie

    async def _post(self, query: str, variables: dict[str, Any]) -> dict:
        headers = {
            "Cookie": self._cookie,
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        try:
            async with async_timeout.timeout(REQUEST_TIMEOUT):
                async with self._session.post(
                    API_URL,
                    headers=headers,
                    json={"query": query, "variables": variables},
                ) as resp:
                    if resp.status in (401, 403):
                        raise AuthenticationError(
                            f"Helthjem session cookie rejected (HTTP {resp.status})"
                        )
                    resp.raise_for_status()
                    payload = await resp.json(content_type=None)
        except AuthenticationError:
            raise
        except TimeoutError as err:
            raise ProviderTimeoutError("Timed out talking to Helthjem") from err
        except aiohttp.ClientError as err:
            raise ProviderConnectionError(str(err)) from err

        errors = payload.get("errors") if isinstance(payload, dict) else None
        if errors:
            messages = "; ".join(str(e.get("message", "")) for e in errors)
            if any(
                token in messages.upper()
                for token in ("UNAUTHENTICATED", "UNAUTHORIZED", "FORBIDDEN")
            ):
                raise AuthenticationError(
                    "Helthjem session cookie is not accepted; please re-authenticate"
                )
            raise ProviderError(f"Helthjem GraphQL error: {messages}")

        return payload.get("data") or {}

    async def async_get_packages(self) -> list[dict]:
        """Return the user's incoming packages (list view, thin data)."""
        data = await self._post(
            LIST_QUERY,
            {
                "page": 1,
                "size": LIST_PAGE_SIZE,
                "types": INCOMING_TYPES,
                "showHidden": False,
            },
        )
        packages = (data.get("getUserPackages") or {}).get("data")
        return packages or []

    async def async_get_details(self, reference: str) -> dict | None:
        """Return rich tracking details for one parcel reference."""
        data = await self._post(DETAIL_QUERY, {"parcelReference": reference})
        return data.get("getParcelTrackingDetails")

    async def async_get_default_recipient(self) -> dict | None:
        """Return the user's default recipient address ({city, zipCode})."""
        data = await self._post(USER_QUERY, {})
        addresses = (data.get("getLoggedUser") or {}).get("recipientAddresses") or []
        if not addresses:
            return None
        return next(
            (a for a in addresses if a.get("default")),
            addresses[0],
        )
