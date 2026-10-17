from pathlib import Path
import pytest
from src.infrastructure.crawler.scrapy_crawler_executor import ScrapyCrawlerExecutor
from unittest.mock import Mock
def test_execute_rejects_blank_crawl_run_id(valid_config_data, tmp_path):
    from src.domain.entities.crawler_config import CrawlerConfig

    # Arrange
    config = CrawlerConfig.model_validate(valid_config_data)
    worker_path = tmp_path / "worker.py"
    executor = ScrapyCrawlerExecutor(worker_path=worker_path)

    # Act & Assert
    with pytest.raises(
        ValueError,
        match="crawl_run_id must not be blank",
    ):
        executor.execute(config, "   ")
