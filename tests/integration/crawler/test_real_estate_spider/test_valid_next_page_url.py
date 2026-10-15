from scrapy.http import HtmlResponse, Request
from scrapy.utils.test import get_crawler
from unittest.mock import Mock
from src.infrastructure.crawler.spiders.real_estate_spider import RealEstateSpider  
from src.domain.entities.crawler_config import CrawlerConfig
from scrapy.statscollectors import MemoryStatsCollector
def test_spider_schedules_valid_next_page(valid_config_data):
    config = CrawlerConfig(**valid_config_data)
    crawler = get_crawler(RealEstateSpider)

    spider = RealEstateSpider.from_crawler(
        crawler,
        config=config,
        crawl_run_id="run-test-001",
        event_builder=Mock(),
    )
    crawler.stats = MemoryStatsCollector(crawler)

    request = Request(url="https://example.com/buy")
    response = HtmlResponse(
        url=request.url,
        request=request,
        body=b"""
        <div class="listing">
          <a class="detail-link" href="/property/123">Listing</a>
        </div>
        <a class="next" href="/buy?page=2">Next</a>
        """,
        encoding="utf-8",
    )

    results = list(spider.parse(response))

    next_requests = [
        item for item in results
        if isinstance(item, Request)
    ]

    assert len(next_requests) == 1
    assert next_requests[0].url == "https://example.com/buy?page=2"
    assert next_requests[0].callback == spider.parse
    assert next_requests[0].errback == spider.handle_request_error
    assert spider._pages_scheduled == 2
    assert "https://example.com/buy?page=2" in spider._seen_pages
    assert crawler.stats.get_value("pagination/pages_scheduled") == 1


