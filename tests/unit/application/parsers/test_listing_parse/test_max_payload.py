from src.application.parsers.listings_parser import ListingParser
import pytest
@pytest.mark.parametrize(
    "invalid_payload",
    [ 0, -1, -100,],
)
def test_listing_parser_rejects_invalid_max_payload(invalid_payload):
    with pytest.raises(ValueError, match="max_payload_chars must be positive or None"):
        ListingParser(
            source="example_site",
            selectors={
                "item": "div.listing",
                "url": "a.detail-link::attr(href)",
                "title": "h2.title::text",
            },
            allowed_domains=["example.com"],
            max_payload_chars = invalid_payload,
        )
def test_listing_parser_with_pay_load_not_int():
    with pytest.raises(TypeError, match="max_payload_chars must be an int or None"):
        ListingParser(
            source="example_site",
            selectors={
                "item": "div.listing",
                "url": "a.detail-link::attr(href)",
                "title": "h2.title::text",
            },
            allowed_domains=["example.com"],
            max_payload_chars = "True",
        )
