
from scrapy.http import HtmlResponse, Request

from src.application.parsers.listings_parser import ListingParser


def test_parse_with_stats_for_two_valid_listings():
    html = """
    <html>
        <body>
            <div class="listing">
                <a href="/bat-dong-san/123">Căn hộ A</a>
            </div>

            <div class="listing">
                <a href="/bat-dong-san/456">Căn hộ B</a>
            </div>
        </body>
    </html>
    """

    response = HtmlResponse(
        url="https://example.com/tin-dang",
        body=html.encode("utf-8"),
        encoding="utf-8",
        request=Request(url="https://example.com/tin-dang"),
    )

    parser = ListingParser(
        source="example",
        selectors={
            "item": ".listing",
            "url": "a::attr(href)",
            "title": "a::text",
        },
        allowed_domains=["example.com"],
    )

    listings, stats = parser.parse_with_stats(response)

    assert len(listings) == 2

    assert {
        listing.url for listing in listings
    } == {
        "https://example.com/bat-dong-san/123",
        "https://example.com/bat-dong-san/456",
    }

    assert stats.items_found == 2
    assert stats.invalid_url == 0
    assert stats.duplicate_url == 0