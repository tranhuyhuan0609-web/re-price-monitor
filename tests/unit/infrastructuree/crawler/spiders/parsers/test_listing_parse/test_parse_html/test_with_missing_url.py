from src.infrastructure.crawler.spiders.parsers.listings_parser import ListingParser
from scrapy.http import TextResponse
def test_listing_parser_parses_html_with_missing_url():
    html = """
    <html>
        <body>
            <div class="listing">
                <a class="detail-link"></a>
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
    assert len(listings) == 0
