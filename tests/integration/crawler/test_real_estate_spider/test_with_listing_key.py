
from src.application.parsers.listings_parser import ParsedListing


def test_listing_key_is_same_when_source_and_id_are_same_but_url_differs():
    listing_1 = ParsedListing(
        source="batdongsan",
        source_listing_id="123",
        url="https://example.com/property/123",
        url_hash="hash_1",
    )

    listing_2 = ParsedListing(
        source="batdongsan",
        source_listing_id="123",
        url="https://example.com/detail/123",
        url_hash="hash_2",
    )

    assert listing_1.listing_key == listing_2.listing_key


def test_listing_key_is_different_when_source_differs_but_id_is_same():
    listing_1 = ParsedListing(
        source="batdongsan",
        source_listing_id="123",
        url="https://example.com/property/123",
        url_hash="hash_1",
    )

    listing_2 = ParsedListing(
        source="chotot",
        source_listing_id="123",
        url="https://example.com/property/123",
        url_hash="hash_1",
    )

    assert listing_1.listing_key != listing_2.listing_key


def test_listing_key_is_same_when_source_id_is_missing_and_url_hash_is_same():
    listing_1 = ParsedListing(
        source="batdongsan",
        source_listing_id=None,
        url="https://example.com/property/123",
        url_hash="same_hash",
    )

    listing_2 = ParsedListing(
        source="batdongsan",
        source_listing_id=None,
        url="https://example.com/property/123",
        url_hash="same_hash",
    )

    assert listing_1.listing_key == listing_2.listing_key