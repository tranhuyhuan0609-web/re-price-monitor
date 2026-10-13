from src.infrastructure.crawler.spiders.parsers.listings_parser import ListingParser
import pytest
def test_listing_parser_raises_value_error_with_missing_item_selector():
    # Arrange
    selectors = {
        "url": "a.detail-link::attr(href)",
    }
    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        ListingParser(
            source="ExampleSite",
            selectors=selectors,
            allowed_domains=["Example.com"],
        )
    assert str(exc_info.value) == "Missing required selectors: ['item']"

def test_listing_parser_raises_value_error_with_missing_url_selector():
    # Arrange
    selectors = {
        "item": "div.listing",
    }
    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        ListingParser(
            source="ExampleSite",
            selectors=selectors,
            allowed_domains=["Example.com"],
        )
    assert str(exc_info.value) == "Missing required selectors: ['url']"
def test_listing_parser_raises_value_error_with_unknown_selectors():
    # Arrange
    selectors = {
        "item": "div.listing",
        "url": "a.detail-link::attr(href)",
        "unknown_selector": "div.unknown"
    }
    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        ListingParser(
            source="ExampleSite",
            selectors=selectors,
            allowed_domains=["Example.com"],
        )
    assert str(exc_info.value) == "Unknown selector keys: ['unknown_selector']; allowed: ['contact_info', 'description', 'item', 'raw_address', 'raw_area', 'raw_price', 'source_listing_id', 'title', 'url']"