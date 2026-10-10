from src.domain.entities.property_listing import ListingLifecycle
def test_with_valid_value():
    lifecycle = ListingLifecycle(
        listing_key="listing_123",
        status="active",
        missing_count=0,
        last_seen_at="2023-01-01T00:00:00Z",
        ended_at=None,
    )

    assert True