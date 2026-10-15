import pytest

from src.application.parsers.listings_parser import ListingParser
@pytest.mark.parametrize(
    "invalid_selector",
    [
        "",
        "   ",
        None,
        123,
    ],
)
def test_listing_parser_rejects_invalid_selector_value(
    invalid_selector,
):
    selectors = {
        "item": "div.listing",
        "url": "a.detail-link::attr(href)",
        "title": invalid_selector,
    }

    with pytest.raises(
        ValueError,
        match="Selector 'title' must be a non-empty string",
    ):
        ListingParser(
            source="example_site",
            selectors=selectors,
            allowed_domains=["example.com"],
        )