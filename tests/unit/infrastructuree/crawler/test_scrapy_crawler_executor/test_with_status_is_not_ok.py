from src.domain.entities.crawler_config import CrawlerConfig
from src.infrastructure.crawler.scrapy_crawler_executor import ScrapyCrawlerExecutor
from unittest.mock import Mock
import subprocess
import json
import pytest
def test_execute_raises_error_when_worker_status_is_not_ok(
    valid_config_data,
    tmp_path,
    monkeypatch,
):
    config = CrawlerConfig.model_validate(valid_config_data)

    worker_path = tmp_path / "scrapy_worker.py"
    worker_path.touch()

    executor = ScrapyCrawlerExecutor(worker_path=worker_path)

    run_mock = Mock(
        return_value=subprocess.CompletedProcess(
            args=["python", str(worker_path)],
            returncode=0,
            stdout=json.dumps(
                {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": "Crawler configuration is invalid",
                }
            ),
            stderr="",
        )
    )

    monkeypatch.setattr(
        "src.infrastructure.crawler.scrapy_crawler_executor.subprocess.run",
        run_mock,
    )

    with pytest.raises(
        RuntimeError,
        match="Worker error: ValueError: Crawler configuration is invalid",
    ):
        executor.execute(config, "run-001")

    run_mock.assert_called_once()
