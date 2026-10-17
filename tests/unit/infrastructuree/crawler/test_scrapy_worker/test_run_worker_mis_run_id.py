from src.infrastructure.crawler import scrapy_worker
import pytest
from src.domain.entities.crawler_config import CrawlerConfig
def test_run_worker_rejects_missing_crawl_run_id(valid_config_data):
    # Arrange: tạo payload thiếu crawl_run_id
    config = CrawlerConfig.model_validate(valid_config_data)
    payload = {
        "config_json": config.model_dump_json(),
    }

    # Act & Assert: worker phải từ chối chạy crawler
    with pytest.raises(ValueError, match="crawl_run_id must be a non-empty string"):
        scrapy_worker.run_worker(payload)