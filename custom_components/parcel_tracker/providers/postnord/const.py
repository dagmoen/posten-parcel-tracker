"""Constants for the PostNord provider.

The PostNord Norge web app (app.postnord.no) is a Vue/Inertia PWA whose account
parcel list comes from a simple cookie-authenticated endpoint. Determined by
inspecting the web app's network traffic; this is an UNOFFICIAL, undocumented
API and may change. See the project README for caveats.
"""

from __future__ import annotations

API_BASE = "https://app.postnord.no"
SHIPMENTS_PATH = "/api/user/shipments"

# A desktop browser User-Agent; the endpoint is the web app's own API.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

CARRIER_NAME = "PostNord"

REQUEST_TIMEOUT = 30
