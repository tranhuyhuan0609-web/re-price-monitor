from src.infrastructure.crawler.scrapy_crawler_executor import (
    ScrapyCrawlerExecutor,
)
import subprocess
from unittest.mock import Mock

import pytest
from src.domain.entities.crawler_config import CrawlerConfig
def test_execute_raises_timeout_error_when_worker_times_out(
    valid_config_data,
    tmp_path,
    monkeypatch,
):
    config = CrawlerConfig.model_validate(valid_config_data)

    worker_path = tmp_path / "scrapy_worker.py"
    worker_path.touch()

    executor = ScrapyCrawlerExecutor(
        timeout_seconds=10,
        worker_path=worker_path,
    )

    run_mock = Mock(
        side_effect=subprocess.TimeoutExpired(
            cmd=["python", str(worker_path)],
            timeout=10,
        )
    )
    monkeypatch.setattr(
        "src.infrastructure.crawler.scrapy_crawler_executor.subprocess.run",
        run_mock,
    )

    with pytest.raises(
        TimeoutError,
        match="Scrapy worker timed out after 10s",
    ):
        executor.execute(config, "run-001")

    run_mock.assert_called_once()
