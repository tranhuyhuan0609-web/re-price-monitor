from src.domain.entities.property_listing import ListingLifecycle
from pydantic import ValidationError
import pytest
def test_with_inactive_but_count_not_equals_5():
    with pytest.raises(ValidationError):
        ListingLifecycle(
            listing_key="listing_123",
            status="inactive",
            missing_count=3,
            last_seen_at="2023-01-01T00:00:00Z",
            ended_at="2023-01-02T00:00:00Z",
        )