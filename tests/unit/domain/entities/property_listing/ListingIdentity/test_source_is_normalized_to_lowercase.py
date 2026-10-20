from src.domain.entities.property_listing import ListingIdentity
def test_source_is_normalized_to_lowercase():
    listing = ListingIdentity(
        source="TEST-SOURCE",
        url="https://example.com/listing/12345",
        url_hash="a" * 64,
    )

    assert listing.source == "test-source"
    assert listing.listing_key == "test-source:url:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"