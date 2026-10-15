from src.infrastructure.crawler.spiders.real_estate_spider import RealEstateSpider
from src.domain.entities.crawler_config import CrawlerConfig
from scrapy.http import Response, Request
from scrapy.utils.test import get_crawler
from scrapy.statscollectors import MemoryStatsCollector
from unittest.mock import Mock

def test_spider_skips_non_text_response(valid_config_data):
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

    request = Request(url="https://example.com/buy")
    response = Response(
        url=request.url,
        request=request,
        body=b"\x00\x01\x02",
    )

    results = list(spider.parse(response))

    assert results == []
    builder.build.assert_not_called()
    assert crawler.stats.get_value("listing/non_text_response") == 1
