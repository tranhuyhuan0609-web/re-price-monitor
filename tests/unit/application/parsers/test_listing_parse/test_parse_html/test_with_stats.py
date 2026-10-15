
from scrapy.http import HtmlResponse, Request

from src.application.parsers.listings_parser import ListingParser


def test_parse_with_stats_counts_invalid_url():
    html = """
    <html>
        <body>
            <div class="listing">
                <a href="/bat-dong-san/123">Căn hộ A</a>
            </div>

            <div class="listing">
                <a href="">Listing không có URL</a>
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
    assert len(listings) == 1
    assert listings[0].url == "https://example.com/bat-dong-san/123"
    assert stats.items_found == 2
    assert stats.invalid_url == 1
    assert stats.duplicate_url == 0