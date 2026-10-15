from src.domain.entities.crawler_config import CrawlerConfig
from scrapy.crawler import CrawlerRunner
from scrapy.settings import Settings
from unittest.mock import Mock
from src.infrastructure.crawler.spiders.real_estate_spider import RealEstateSpider
def test_spider_generates_initial_requests(valid_config_data):
    config = CrawlerConfig(**valid_config_data)
    builder = Mock()
    runner = CrawlerRunner(Settings())
    crawler = runner.create_crawler(RealEstateSpider)

    spider = crawler.spidercls.from_crawler(
        crawler,
        config=config,
        crawl_run_id="run-test-001",
        event_builder=builder,
    )

    requests = list(spider._initial_requests())

    assert len(requests) == len(config.start_urls)

    for request, start_url in zip(requests, config.start_urls):
        assert request.url == str(start_url)
        assert request.callback == spider.parse
        assert request.errback == spider.handle_request_error
        assert request.dont_filter is True