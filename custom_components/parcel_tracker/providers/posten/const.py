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

# The parcel list is a POST that returns parcels updated after ``lastUpdated``,
# in pages. The app uses this for incremental sync; we instead request a rolling
# window (only active + recently-delivered parcels are relevant to Home
# Assistant) and page through it via the ``exclude`` cursor. A large lookback
# would drag in dozens of old archived parcels for no benefit.
PARCEL_LOOKBACK_DAYS = 30
PARCEL_MAX_PAGES = 50

APP_VERSION = "8.3.2"
USER_AGENT = f"posten/{APP_VERSION} Android/13"

# Public tracking deep-link (used to build a tracking_url attribute).
TRACKING_URL_TEMPLATE = "https://sporing.posten.no/sporing/{parcel_id}"

CARRIER_NAME = "Posten/Bring"

REQUEST_TIMEOUT = 30
