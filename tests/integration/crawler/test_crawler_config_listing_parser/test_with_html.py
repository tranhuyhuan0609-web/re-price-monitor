from scrapy.http import Request, TextResponse

from src.domain.entities.crawler_config import CrawlerConfig
from src.application.parsers.listings_parser import ListingParser
def test_crawler_config_can_initialize_listing_parser_with_html_content(
    valid_config_data,
):
    config = CrawlerConfig(**valid_config_data)
    parser = ListingParser(
        source=config.site_id,
        selectors=config.selectors.to_parser_dict(),
        allowed_domains=config.allowed_domains,
    )
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
        request=Request(url="https://example.com/tin-dang"),
    )
    listings,stats = parser.parse_with_stats(response)
    assert len(listings) == 1
    assert listings[0].url == "https://example.com/bat-dong-san/123"