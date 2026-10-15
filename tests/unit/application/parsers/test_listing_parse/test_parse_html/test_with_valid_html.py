from scrapy.http import TextResponse
from src.application.parsers.listings_parser import ListingParser
from src.application.exceptions.listing_parse_exception import ListingParseError
import pytest
def test_listing_parser_parses_valid_html():
    html = """
    <html>
        <body>
            <div class="listing">
                <a class="detail-link" href="/bat-dong-san/123">
                    Căn hộ Hà Nội
                </a>
            </div>
        </body>
    </html>
    """

    response = TextResponse(
        url="https://example.com/tin-dang",
        body=html.encode("utf-8"),
        encoding="utf-8",
    )

    selectors = {
        "item": "div.listing",
        "url": "a.detail-link::attr(href)",
        "title": "a.detail-link::text",
    }

    parser = ListingParser(
        source="example_site",
        selectors=selectors,
        allowed_domains=["example.com"],
    )

    listings = parser.parse(response)

    assert len(listings) == 1

    listing = listings[0]

    assert listing.url == "https://example.com/bat-dong-san/123"
    assert listing.title.strip() == "Căn hộ Hà Nội"
def test_listing_parser_parses_html_with_missing_optional_fields():
    html = """
    <html>
        <body>
            <div class="listing">
                <a class="detail-link" href="/bat-dong-san/123"></a>
            </div>
        </body>
    </html>
    """

    response = TextResponse(
        url="https://example.com/tin-dang",
        body=html.encode("utf-8"),
        encoding="utf-8",
    )

    selectors = {
        "item": "div.listing",
        "url": "a.detail-link::attr(href)",
        "title": "a.detail-link::text",
    }

    parser = ListingParser(
        source="example_site",
        selectors=selectors,
        allowed_domains=["example.com"],
    )

    listings = parser.parse(response)

    assert len(listings) == 1

    listing = listings[0]

    assert listing.url == "https://example.com/bat-dong-san/123"
    assert listing.title == None
    assert listing.quality_flags == ("missing_title",)
