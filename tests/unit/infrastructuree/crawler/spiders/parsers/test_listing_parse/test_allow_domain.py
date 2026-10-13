from src.infrastructure.crawler.spiders.parsers.listings_parser import ListingParser
import pytest
def test_listing_parser_with_none_allowed_domains():
    # Arrange
    selectors = {
        "item": "div.listing",
        "url": "a.detail-link::attr(href)",
    }
    with pytest.raises(ValueError, match="allowed_domains must be a non-empty list"):
        ListingParser(
            source="ExampleSite",
            selectors=selectors,
            allowed_domains=None,
        )
def test_listing_parser_with_duplicate_allowed_domains():
    # Arrange
    selectors = {
        "item": "div.listing",
        "url": "a.detail-link::attr(href)",
    }
    parser = ListingParser(
        source="ExampleSite",
        selectors=selectors,
        allowed_domains=["example.com", "Example.com"],
    )
    assert parser.allowed_domains == frozenset({"example.com"})
    assert len(parser.allowed_domains) == 1
def test_listing_parser_with_empty_allowed_domains():
    selectors = {
        "item": "div.listing",
        "url": "a.detail-link::attr(href)",
    }
    with pytest.raises(ValueError, match="Each allowed domain must be non-empty"):
        parser = ListingParser(
            source="ExampleSite",
            selectors=selectors,
            allowed_domains=["example.com.", " "],
        )
        assert parser.allowed_domains == frozenset({"example.com."})