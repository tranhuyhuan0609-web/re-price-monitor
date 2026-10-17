from pathlib import Path
from unittest.mock import Mock

import pytest
from src.domain.entities.crawler_config import CrawlerConfig
from src.infrastructure.crawler.scrapy_crawler_executor import (
    ScrapyCrawlerExecutor,
)


def test_execute_raises_when_worker_path_does_not_exist(
    valid_config_data,
    tmp_path: Path,
    monkeypatch,
):
    # Arrange
    missing_worker = tmp_path / "missing_worker.py"
    executor = ScrapyCrawlerExecutor(worker_path=missing_worker)
    config = CrawlerConfig.model_validate(valid_config_data)

    subprocess_run = Mock()
    monkeypatch.setattr(
        "src.infrastructure.crawler.scrapy_crawler_executor.subprocess.run",
        subprocess_run,
    )

    # Act & Assert
    with pytest.raises(FileNotFoundError, match="Scrapy worker not found"):
        executor.execute(config, "run-001")

    # Không được khởi chạy subprocess nếu worker không tồn tại
    subprocess_run.assert_not_called()
