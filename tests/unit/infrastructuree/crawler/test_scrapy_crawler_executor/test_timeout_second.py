import pytest
from src.infrastructure.crawler.scrapy_crawler_executor import (
    ScrapyCrawlerExecutor,
)


def test_init_rejects_zero_timeout_seconds():
    with pytest.raises(
        ValueError,
        match="timeout_seconds must be a positive integer",
    ):
        ScrapyCrawlerExecutor(timeout_seconds=0)
def test_init_rejects_bool_timeout_seconds():
    with pytest.raises(
        ValueError,
        match="timeout_seconds must be a positive integer",
    ):
        ScrapyCrawlerExecutor(timeout_seconds=True)

