
from src.application.parsers.listings_parser import ParsedListing
def make_listing(
    *,
    source: str = "site_a",
    url: str = "https://example.com/property/123",
    url_hash: str = "hash_123",
    source_listing_id: str | None = None,
) -> ParsedListing:
    return ParsedListing(
        source=source,
        url=url,
        url_hash=url_hash,
        source_listing_id=source_listing_id,
    )


def test_listing_key_uses_source_and_source_listing_id() -> None:
    listing = make_listing(
        source="site_a",
        source_listing_id="123",
        url_hash="hash_123",
    )

    assert listing.listing_key == "site_a:123"


def test_listing_key_falls_back_to_url_hash_when_id_is_missing() -> None:
    listing = make_listing(
        source="site_a",
        source_listing_id=None,
        url_hash="hash_abc",
    )

    assert listing.listing_key == "site_a:url:hash_abc"


def test_same_source_and_id_produce_same_key_even_when_url_differs() -> None:
    listing_a = make_listing(
        source="site_a",
        url="https://example.com/property/123",
        url_hash="hash_123",
        source_listing_id="123",
    )
    listing_b = make_listing(
        source="site_a",
        url="https://example.com/listing/123",
        url_hash="different_hash",
        source_listing_id="123",
    )

    assert listing_a.listing_key == listing_b.listing_key