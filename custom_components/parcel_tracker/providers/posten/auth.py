"""OAuth2 authentication against id.posten.no.

The Posten app uses the OAuth2 authorization-code grant:

1. Open ``{ID_BASE}{OAUTH_SERVICE}/authorizations/new`` in a browser, where the
   user authenticates (BankID). The browser is redirected to
   ``posten://login?code=...`` — a custom scheme Home Assistant cannot receive,
   so the user pastes the code back manually.
2. Exchange the code at ``{ID_BASE}{OAUTH_SERVICE}/accesstoken`` for an
   access/refresh token pair, authenticating the *client* with an HTTP Basic
   header built from the app's client id and secret.
3. Refresh the access token with the ``refresh_token`` grant.

This module has no Home Assistant dependency; it only needs an aiohttp session.
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode, urlparse

import aiohttp
import async_timeout

from .. import AuthenticationError, ProviderConnectionError, ProviderTimeoutError
from .const import (
    CLIENT_ID,
    CLIENT_SECRET,
    ID_BASE,
    OAUTH_AUTHORIZE_PATH,
    OAUTH_SERVICE,
    OAUTH_TOKEN_PATH,
    REDIRECT_URI,
    REQUEST_TIMEOUT,
    USER_AGENT,
)


def _basic_auth_header() -> str:
    """Return the ``Basic ...`` header value for the token endpoint."""
    raw = f"{CLIENT_ID}:{CLIENT_SECRET}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def build_authorize_url(state: str, lang: str = "no") -> str:
    """Return the URL the user must open in a browser to log in."""
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "platform": "Android",
        "state": state,
        "lang": lang,
        "is_app": "true",
    }
    return f"{ID_BASE}{OAUTH_SERVICE}/{OAUTH_AUTHORIZE_PATH}?{urlencode(params)}"


def extract_code(pasted: str) -> str:
    """Extract the authorization code from user-pasted input.

    Accepts either the bare code, or the full ``posten://login?code=...&state=..``
    redirect URL that the browser lands on after login.
    """
    value = pasted.strip()
    if not value:
        raise AuthenticationError("No authorization code provided")

    looks_like_url = "://" in value or "?" in value
    if looks_like_url:
        # Custom-scheme URLs parse fine with urlparse for the query part.
        query = urlparse(value).query or value.split("?", 1)[-1]
        codes = parse_qs(query).get("code")
        if codes and codes[0]:
            return codes[0]
        raise AuthenticationError("Could not find 'code' in the pasted URL")

    return value


@dataclass(slots=True)
class Token:
    """OAuth token pair with an absolute expiry timestamp."""

    access_token: str
    refresh_token: str
    expires_at: float

    @property
    def is_expired(self) -> bool:
        # Refresh a minute early to avoid using a token mid-flight.
        return time.time() >= (self.expires_at - 60)


class PostenAuth:
    """Handles token exchange and refresh; holds the current token."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        *,
        refresh_token: str | None = None,
        access_token: str | None = None,
        expires_at: float = 0.0,
    ) -> None:
        self._session = session
        self._token: Token | None = None
        if refresh_token:
            self._token = Token(
                access_token=access_token or "",
                refresh_token=refresh_token,
                expires_at=expires_at,
            )

    @property
    def token(self) -> Token | None:
        return self._token

    async def async_exchange_code(self, code: str) -> Token:
        """Exchange an authorization code for a token pair."""
        data = {
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "grant_type": "authorization_code",
        }
        self._token = await self._async_token_request(data)
        return self._token

    async def async_refresh(self) -> Token:
        """Refresh the access token using the stored refresh token."""
        if self._token is None or not self._token.refresh_token:
            raise AuthenticationError("No refresh token available")
        data = {
            "refresh_token": self._token.refresh_token,
            "grant_type": "refresh_token",
        }
        self._token = await self._async_token_request(data)
        return self._token

    async def async_valid_access_token(self) -> str:
        """Return a valid access token, refreshing if necessary."""
        if self._token is None:
            raise AuthenticationError("Not authenticated")
        if self._token.is_expired or not self._token.access_token:
            await self.async_refresh()
        return self._token.access_token

    async def _async_token_request(self, data: dict[str, str]) -> Token:
        url = f"{ID_BASE}{OAUTH_SERVICE}/{OAUTH_TOKEN_PATH}"
        headers = {
            "Authorization": _basic_auth_header(),
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        }
        try:
            async with async_timeout.timeout(REQUEST_TIMEOUT):
                async with self._session.post(
                    url, data=data, headers=headers
                ) as resp:
                    if resp.status in (400, 401, 403):
                        raise AuthenticationError(
                            f"Token request rejected (HTTP {resp.status})"
                        )
                    resp.raise_for_status()
                    payload = await resp.json(content_type=None)
        except AuthenticationError:
            raise
        except TimeoutError as err:
            raise ProviderTimeoutError("Timed out talking to id.posten.no") from err
        except aiohttp.ClientError as err:
            raise ProviderConnectionError(str(err)) from err

        return self._parse_token(payload)

    @staticmethod
    def _parse_token(payload: dict) -> Token:
        access = payload.get("access_token")
        refresh = payload.get("refresh_token")
        expires_in = payload.get("expires_in", 3600)
        if not access or not refresh:
            raise AuthenticationError("Token response missing access/refresh token")
        try:
            expires_at = time.time() + float(expires_in)
        except (TypeError, ValueError):
            expires_at = time.time() + 3600
        return Token(
            access_token=str(access),
            refresh_token=str(refresh),
            expires_at=expires_at,
        )
