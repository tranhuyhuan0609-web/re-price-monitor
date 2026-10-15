from unittest.mock import Mock
from scrapy.crawler import CrawlerRunner
from scrapy.settings import Settings

from src.domain.entities.crawler_config import CrawlerConfig
from src.infrastructure.crawler.spiders.real_estate_spider import RealEstateSpider


def test_spider_initializes_from_validated_config(valid_config_data):
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

    assert spider.config is config
    assert spider.crawl_run_id == "run-test-001"
    assert spider.event_builder is builder
    assert spider.start_urls == [str(url) for url in config.start_urls]
    assert spider.allowed_domains == config.allowed_domains
