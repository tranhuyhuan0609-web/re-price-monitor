from src.domain.entities.crawler_config import CrawlerConfig
from src.infrastructure.crawler.spiders.real_estate_spider import RealEstateSpider
from scrapy.settings import Settings
from scrapy.utils.test import get_crawler
from unittest.mock import Mock
from scrapy.http import HtmlResponse, Request
from scrapy.statscollectors import MemoryStatsCollector
def test_spider_stop_pagination_with_no_listing(valid_config_data):
    config = CrawlerConfig(**valid_config_data)
    builder = Mock()
    crawler = get_crawler(RealEstateSpider)
    spider = RealEstateSpider.from_crawler(
        crawler,
        config=config,
        crawl_run_id="run-test-001",
        event_builder=builder,
    )
    crawler.stats = MemoryStatsCollector(crawler)

    html_no_listings = """
    <html>
      <body>
        <div class="no-listings">No listings found</div>
      </body>
    </html>
    """

    request = Mock()
    request.url = "https://example.com/buy"
    
    response_no_listings = HtmlResponse(
        url=request.url,
        request=request,
        body=html_no_listings.encode("utf-8"),
        encoding="utf-8",
    )

    results = list(spider.parse(response_no_listings))
    assert len(results) == 0
    assert builder.build.call_count == 0