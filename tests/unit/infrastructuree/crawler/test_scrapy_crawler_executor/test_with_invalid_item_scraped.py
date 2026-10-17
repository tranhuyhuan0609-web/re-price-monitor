from src.domain.entities.crawler_config import CrawlerConfig
from src.infrastructure.crawler.scrapy_crawler_executor import ScrapyCrawlerExecutor
import subprocess
from unittest.mock import Mock
import pytest
import json
def test_execute_raises_error_when_items_scraped_is_negative(
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
                    "crawl_run_id": "run-001",
                    "items_scraped": -1,
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
        match="Invalid items_scraped in worker result",
    ):
        executor.execute(config, "run-001")

    run_mock.assert_called_once()

def test_execute_raises_error_when_items_scraped_is_string(
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
                    "crawl_run_id": "run-001",
                    "items_scraped": "not a number",
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
        match="Invalid items_scraped in worker result",
    ):
        executor.execute(config, "run-001")

    run_mock.assert_called_once()

def test_execute_raises_error_when_items_scraped_is_negative(
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
                    "crawl_run_id": "run-001",
                    "items_scraped": -1,
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
        match="Invalid items_scraped in worker result",
    ):
        executor.execute(config, "run-001")

    run_mock.assert_called_once()

