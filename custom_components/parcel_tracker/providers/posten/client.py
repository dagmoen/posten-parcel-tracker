"""HTTP client for the Posten parcel API."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

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
    PARCEL_LOOKBACK_DAYS,
    PARCEL_MAX_PAGES,
    PARCEL_SERVICE,
    REQUEST_TIMEOUT,
    USER_AGENT,
)


class PostenClient:
    """Thin wrapper over the api.posten.no parcel endpoints."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        auth: PostenAuth,
        lookback_days: int = PARCEL_LOOKBACK_DAYS,
    ) -> None:
        self._session = session
        self._auth = auth
        self._lookback_days = max(int(lookback_days), 1)

    async def async_get_parcels_raw(self) -> dict[str, list]:
        """Fetch the parcels updated within the lookback window.

        The endpoint is a POST that returns parcels updated after ``lastUpdated``
        in pages, along with ``remainingCount``. We advance through the pages by
        adding each returned ``parcelNumber`` to ``exclude`` until nothing
        remains, then return the combined list under a ``parcels`` key.
        """
        access_token = await self._auth.async_valid_access_token()
        url = f"{API_BASE}{PARCEL_SERVICE}/{PARCEL_LIST_PATH}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Content-Type": "application/json",
            # Ask Posten for Norwegian event descriptions / tracking text.
            "Accept-Language": "nb-NO",
        }
        since = (
            datetime.now(timezone.utc) - timedelta(days=self._lookback_days)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        parcels: list = []
        exclude: list[str] = []
        try:
            for _ in range(PARCEL_MAX_PAGES):
                body = {"lastUpdated": since, "exclude": list(exclude)}
                async with async_timeout.timeout(REQUEST_TIMEOUT):
                    async with self._session.post(
                        url, headers=headers, json=body
                    ) as resp:
                        if resp.status in (401, 403):
                            raise AuthenticationError(
                                f"Parcel request unauthorized (HTTP {resp.status})"
                            )
                        resp.raise_for_status()
                        data = await resp.json(content_type=None)

                batch = data.get("parcels") if isinstance(data, dict) else None
                if not batch:
                    break
                parcels.extend(batch)
                exclude.extend(
                    p["parcelNumber"]
                    for p in batch
                    if isinstance(p, dict) and p.get("parcelNumber")
                )
                if data.get("remainingCount", 0) <= 0:
                    break
        except AuthenticationError:
            raise
        except TimeoutError as err:
            raise ProviderTimeoutError("Timed out talking to api.posten.no") from err
        except aiohttp.ClientError as err:
            raise ProviderConnectionError(str(err)) from err

        return {"parcels": parcels}
