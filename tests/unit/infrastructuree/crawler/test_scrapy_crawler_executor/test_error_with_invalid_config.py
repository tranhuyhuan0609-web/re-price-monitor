import pytest
from src.infrastructure.crawler.scrapy_crawler_executor import ScrapyCrawlerExecutor
def test_execute_rejects_invalid_config_type():
    executor = ScrapyCrawlerExecutor()

    with pytest.raises(
        TypeError,
        match="config must be a CrawlerConfig",
    ):
        executor.execute(
            config={"site_id": "site-001"},
            crawl_run_id="run-001",
        )
