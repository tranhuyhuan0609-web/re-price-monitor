from src.infrastructure.crawler.spiders.parsers.listings_parser import ListingParser
from scrapy.http import TextResponse
def test_listing_parser_html_with_url_different_domain():
    html = """
    <html>
        <body>
            <div class="listing">
                <a class="detail-link" href="https://otherdomain.com/bat-dong-san/123"></a>
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