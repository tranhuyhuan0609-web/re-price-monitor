import pytest
from datetime import datetime, timezone
from decimal import Decimal
from src.domain.entities.property_listing import ListingObservation
@pytest.fixture
def identity_data():
    return {
        
            "source": "batdongsan",
            "source_listing_id": "123",
            "url": "https://example.com/property/123",
            "url_hash": "a" * 64,
    }