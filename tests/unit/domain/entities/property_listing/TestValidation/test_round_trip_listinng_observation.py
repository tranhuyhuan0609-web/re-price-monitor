from src.domain.entities.property_listing import ListingObservation
from decimal import Decimal
from datetime import datetime, timezone
def test_listing_observation_round_trip():
    observation = ListingObservation(
        identity={
            "source": "batdongsan",
            "source_listing_id": "123",
            "url": "https://example.com/property/123",
            "url_hash": "a" * 64,
        },
        listing={
            "title": "Bán căn hộ",
            "transaction_type": "sale",
        },
        price={
            "status": "known",
            "basis": "total",
            "amount": Decimal("5000000000"),
            "currency": "VND",
        },
        details={
            "area_m2": Decimal("100"),
        },
        crawled_at=datetime.now(timezone.utc),
        raw_event_id="event-123",
    )

    original_price_per_m2 = observation.price_per_m2

    data = observation.model_dump()
    restored = ListingObservation.model_validate(data)

    assert restored.price_per_m2 == original_price_per_m2
    assert restored.identity.listing_key == observation.identity.listing_key