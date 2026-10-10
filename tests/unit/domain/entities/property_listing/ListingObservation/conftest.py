import pytest
from decimal import Decimal
from datetime import datetime, timezone
from src.domain.entities.property_listing import ListingObservation
@pytest.fixture
def observation_data():
    return ListingObservation (
        identity={
            "source": "batdongsan",
            "source_listing_id": "123",
            "url": "https://example.com/property/123",
            "url_hash": "a" * 64,
        },
        listing={
            "title": "Bán căn hộ",
            "transaction_type": "sale",
            "published_at": None,
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