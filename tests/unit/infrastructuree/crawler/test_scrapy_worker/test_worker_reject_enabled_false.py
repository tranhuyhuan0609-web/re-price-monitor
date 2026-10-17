import pytest

from src.domain.entities.crawler_config import CrawlerConfig
from src.infrastructure.crawler import scrapy_worker


def test_run_worker_rejects_disabled_crawler(valid_config_data):
    # Arrange: tạo config hợp lệ nhưng crawler bị vô hiệu hóa
    config_data = {
        **valid_config_data,
        "enabled": False,
    }
    config = CrawlerConfig.model_validate(config_data)

    payload = {
        "crawl_run_id": "run-disabled",
        "config_json": config.model_dump_json(),
    }

    # Act & Assert: worker phải từ chối chạy crawler
    with pytest.raises(ValueError, match="is disabled"):
        scrapy_worker.run_worker(payload)
