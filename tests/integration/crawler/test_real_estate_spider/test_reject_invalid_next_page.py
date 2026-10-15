from src.infrastructure.crawler.spiders.real_estate_spider import RealEstateSpider
from src.domain.entities.crawler_config import CrawlerConfig
from scrapy.http import HtmlResponse, Request
from scrapy.utils.test import get_crawler
from unittest.mock import Mock
from scrapy.statscollectors import MemoryStatsCollector
def test_spider_rejects_invalid_next_page_url(valid_config_data):
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
        <a class="next" href="javascript:void(0)">Next</a>
        """,
        encoding="utf-8",
    )

    results = list(spider.parse(response))

    assert len(results) == 1
    assert not any(isinstance(item, Request) for item in results)
    assert crawler.stats.get_value("pagination/rejected_link") == 1