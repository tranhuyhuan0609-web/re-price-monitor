from src.infrastructure.crawler.spiders.real_estate_spider import RealEstateSpider
from src.domain.entities.crawler_config import CrawlerConfig
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.python.failure import Failure
from scrapy.http import HtmlResponse, Request
from scrapy.utils.test import get_crawler
from unittest.mock import Mock
from scrapy.statscollectors import MemoryStatsCollector
def test_spider_records_failed_request(valid_config_data):
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
    failure = Failure(
        HttpError(
            response=HtmlResponse(
                url=request.url,
                request=request,
                status=500,
                body=b"Server Error",
                encoding="utf-8",
            )
        )
    )

    failure.request = request

    spider.handle_request_error(failure)

    assert crawler.stats.get_value("request/failed") == 1