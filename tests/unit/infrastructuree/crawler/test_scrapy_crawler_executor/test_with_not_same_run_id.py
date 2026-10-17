from src.domain.entities.crawler_config import CrawlerConfig
from src.infrastructure.crawler.scrapy_crawler_executor import ScrapyCrawlerExecutor
import subprocess
from unittest.mock import Mock
import json
import pytest
def test_execute_raises_error_when_crawl_run_id_mismatches(
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
                    "status": "ok",
                    "crawl_run_id": "run-002",
                    "items_scraped": 5,
                    "requests_total": 10,
                    "request_failures": 0,
                    "http_responses_ignored": 0,
                    "finish_reason": "finished",
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
        match="Worker crawl_run_id mismatch",
    ):
        executor.execute(config, "run-001")

    run_mock.assert_called_once()
