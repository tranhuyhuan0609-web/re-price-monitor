from pydantic import ValidationError

from src.infrastructure.crawler import scrapy_worker
from src.domain.entities.crawler_config import CrawlerConfig
import pytest
def test_run_worker_rejects_config_is_not_valid_json():
    # Arrange: tạo payload thiếu crawl_run_id
    payload = {
        "crawl_run_id": "run-001",
        "config_json": "{invalid",
    }

    # Act & Assert: worker phải từ chối chạy crawler
    with pytest.raises(ValueError, match="Worker payload must be valid JSON."):
        scrapy_worker.run_worker(payload)
def test_run_worker_rejects_config_invalid():
    # Arrange: tạo payload với config không hợp lệ
    payload = {
        "crawl_run_id": "run-001",
        "config_json": '{}',
    }

    # Act & Assert: worker phải từ chối chạy crawler
    with pytest.raises(ValidationError):
        scrapy_worker.run_worker(payload)