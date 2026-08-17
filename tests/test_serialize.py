"""Tests for parcel -> dict serialization used by sensor attributes."""

from __future__ import annotations

from datetime import date, datetime, timezone

from custom_components.parcel_tracker.models import Parcel, ParcelEvent, ParcelStatus
from custom_components.parcel_tracker.serialize import parcel_to_dict


def _parcel() -> Parcel:
    return Parcel(
        parcel_id="P1",
        status=ParcelStatus.IN_TRANSIT,
        raw_status="underway",
        carrier="Posten/Bring",
        tracking_number="370701041418816483",
        consignment_number="70701041418803215",
        sender="Fedex Express Norge AS",
        recipient_name="DAG MOEN",
        recipient_address="Ljansbakken 17",
        recipient_postal_code="1169",
        recipient_city="Oslo",
        status_text="underway",
        expected_delivery=date(2026, 8, 13),
        delivery_window_start=datetime(2026, 8, 13, 14, 0, tzinfo=timezone.utc),
        delivery_window_end=datetime(2026, 8, 13, 20, 0, tzinfo=timezone.utc),
        on_track=True,
        delivery_type="home_delivery",
        weight_kg=4.2,
        length_cm=36,
        width_cm=32,
        height_cm=27,
        transport_type="glow",
        events=[
            ParcelEvent(
                description="On its way",
                time=datetime(2026, 8, 13, 10, 7, tzinfo=timezone.utc),
                location="OSLO",
            )
        ],
    )


def test_parcel_to_dict_exposes_all_detail_fields() -> None:
    data = parcel_to_dict(_parcel())
    assert data["kollinummer"] == "370701041418816483"
    assert data["sendingsnummer"] == "70701041418803215"
    assert data["sender"] == "Fedex Express Norge AS"
    assert data["recipient"] == "DAG MOEN"
    assert data["delivery_method"] == "Home delivery"
    assert data["delivery_type"] == "home_delivery"
    # Ready-to-display Norwegian labels for dashboards.
    assert data["status_label"] == "Underveis"
    assert data["delivery_label"] == "Hjemlevering"
    assert data["carrier_dot"] == "🔴"
    assert data["expected_delivery"] == "2026-08-13"
    assert data["delivery_window_start"] == "2026-08-13T14:00:00+00:00"
    assert data["on_track"] is True
    assert data["weight_kg"] == 4.2
    assert data["dimensions"] == "36 × 32 × 27 cm"
    assert data["transport"] == "glow"
    assert len(data["tracking"]) == 1
    assert data["tracking"][0]["description"] == "On its way"
    assert data["tracking"][0]["location"] == "OSLO"


def test_parcel_to_dict_handles_sparse_mailbox_parcel() -> None:
    parcel = Parcel(
        parcel_id="HK1",
        status=ParcelStatus.REGISTERED,
        sender="Helsekost.no",
        delivery_type="mailbox_delivery",
    )
    data = parcel_to_dict(parcel)
    assert data["delivery_method"] == "Mailbox delivery"
    assert data["dimensions"] is None
    assert data["expected_delivery"] is None
    assert data["tracking"] == []
