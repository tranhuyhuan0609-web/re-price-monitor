from src.domain.entities.property_listing import ListingIdentity
def test_listing_key_success():
    listing = ListingIdentity(
        source="test-source",
        url="https://example.com/listing/12345",
        url_hash="a" * 64,
    )

    assert listing.listing_key == "test-source:url:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"