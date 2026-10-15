from src.infrastructure.crawler.spiders.real_estate_spider import RealEstateSpider
from src.domain.entities.crawler_config import CrawlerConfig
from unittest.mock import Mock
from scrapy.http import HtmlResponse, Request
from scrapy.statscollectors import MemoryStatsCollector
from scrapy.utils.test import get_crawler
def test_spider_rejects_next_page_outside_allow_domain(valid_config_data):
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

    
    html = """
    <html>
      <body>
        <div class="listing">
          <a class="detail-link" href="/property/123">
            Can ho Ha Noi
          </a>
        </div>
        <a class="next" href="https://evil.example/buy?page=2">Next</a>
      </body>
    </html>
    """

    request = Mock()
    request.url = "https://example.com/buy"
    
    response_with_next_page_outside_domain = HtmlResponse(
        url=request.url,
        request=request,
        body=html.encode("utf-8"),
        encoding="utf-8",
    )

    results = list(spider.parse(response_with_next_page_outside_domain))
    results_urls = [result.url for result in results if isinstance(result, Request)]
    assert len(results) == 1  # Only the listing should be processed, not the next page
    assert builder.build.call_count == 1  # Only one event should be built for the
    assert len(results_urls) == 0  # No next page request should be generated