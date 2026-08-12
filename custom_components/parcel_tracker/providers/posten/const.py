"""Constants for the Posten/Bring provider.

Endpoint and client details were determined by inspecting the official Posten
Android app. This is an UNOFFICIAL, undocumented API: values here may change if
Posten updates their app. See the project README for the caveats.

URL construction in the app is ``{base}{service}/{path}`` — reproduced below.
"""

from __future__ import annotations

# OAuth2 / identity
ID_BASE = "https://id.posten.no/"
OAUTH_SERVICE = "api/oauth"
OAUTH_AUTHORIZE_PATH = "authorizations/new"
OAUTH_TOKEN_PATH = "accesstoken"

# Public client credentials embedded in the Posten app. These identify the
# official app to the auth server; they are not user secrets.
CLIENT_ID = "f0ad2360e9f64a0986faafe66a9731e5"
# Client secret shipped in the app binary. Used for the HTTP Basic header on the
# token endpoint (base64(client_id:client_secret)). Not a per-user secret.
CLIENT_SECRET = (
    "b814595805d5859ebe1d69abd2e65b0d8f4b786478bb31b5bfeefb5dc5dc1b1be8dae22d83d4195f"
)
REDIRECT_URI = "posten://login"

# API
API_BASE = "https://api.posten.no/"
PARCEL_SERVICE = "parcel-api"
PARCEL_LIST_PATH = "v1/parcel"

APP_VERSION = "8.3.2"
ANDROID_VERSION = "13"
USER_AGENT = f"posten/{APP_VERSION} Android/{ANDROID_VERSION}"

# The official app attaches these identifying headers (via an OkHttp interceptor)
# to every api.posten.no request. The backend expects them and returns HTTP 500
# when they are missing, so we reproduce them here.
ACCEPT_LANGUAGE = "nb-NO,nb;q=0.9,no;q=0.8,en;q=0.7"
PLATFORM = "android"

# Public tracking deep-link (used to build a tracking_url attribute).
TRACKING_URL_TEMPLATE = "https://sporing.posten.no/sporing/{parcel_id}"

CARRIER_NAME = "Posten/Bring"

REQUEST_TIMEOUT = 30
