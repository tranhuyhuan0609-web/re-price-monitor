from src.infrastructure.crawler.spiders.parsers.listings_parser import ListingParser
def test_listing_parser_initializes_with_valid_config():
    # Arrange
    selectors = {
        "item": "div.listing",
        "url": "a.detail-link::attr(href)",
    }
    parser = ListingParser(
        source="  ExampleSite  ",
        selectors=selectors,
        allowed_domains=["Example.com"],
    )
    assert parser.source == "examplesite"
    assert parser.selectors == selectors
    assert parser.allowed_domains == frozenset({"example.com"})
    assert parser.max_payload_chars is None
