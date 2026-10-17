from src.infrastructure.crawler.scrapy_crawler_executor import ScrapyCrawlerExecutor

import pytest
def test_close_spider_timeout_rejects_zero_timeout_seconds():

    with pytest.raises(
        ValueError,
        match="closespider_timeout must be a positive integer",
    ):
        ScrapyCrawlerExecutor(closespider_timeout=0)
def test_close_spider_timeout_rejects_bool_timeout_seconds():
    with pytest.raises(
        ValueError,
        match="closespider_timeout must be a positive integer",
    ):
        ScrapyCrawlerExecutor(closespider_timeout=True)