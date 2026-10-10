from src.domain.entities.property_listing import ListingIdentity
def test_listing_key_falls_back_to_url_hash():
    listing = ListingIdentity(
        source="test-source",
        source_listing_id=None,
        url="https://example.com/listing/12345",
        url_hash="a" * 64,
    )

    assert listing.listing_key == "test-source:url:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"