"""Constants and GraphQL queries for the Helthjem provider.

Helthjem (helthjem.no) is a Norwegian home-delivery carrier with a web app only
(no mobile app). The account parcel list comes from a cookie-authenticated
GraphQL API. Determined by inspecting the web app; this is an UNOFFICIAL,
undocumented API and may change. See the project README for caveats.
"""

from __future__ import annotations

API_URL = "https://services.helthjem.no/graphql"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

CARRIER_NAME = "Helthjem"

REQUEST_TIMEOUT = 30
LIST_PAGE_SIZE = 50

# Incoming parcels (the user is the recipient).
INCOMING_TYPES = ["RECEIVED"]

# List of the user's packages (tracking codes + coarse category).
LIST_QUERY = """
query GetPackages($page: Int!, $size: Int!, $types: [UserStatus!], $showHidden: Boolean = false) {
  getUserPackages(page: $page, size: $size, types: $types, showHidden: $showHidden) {
    pagination { total }
    data {
      id
      trackingCode
      userStatus
      shop { name }
      orderData { recipientAddress { city zipCode } }
    }
  }
}
"""

# The logged-in user's own address (the recipient for incoming parcels), used as
# a fallback when a package has no per-order recipient address.
USER_QUERY = """
query GetUser {
  getLoggedUser {
    recipientAddresses {
      city
      zipCode
      default
    }
  }
}
"""

# Rich per-parcel tracking details (more fields than the web app itself asks for).
DETAIL_QUERY = """
query GetParcel($parcelReference: String!) {
  getParcelTrackingDetails(parcelReference: $parcelReference) {
    parcelReference
    status
    estimatedDelivery { date }
    shop { name }
    servicePoint { name address }
    events { createdAt status location }
  }
}
"""
