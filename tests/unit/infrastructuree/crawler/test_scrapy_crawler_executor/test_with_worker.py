
import json
import subprocess
from unittest.mock import Mock
from src.domain.entities.crawler_config import CrawlerConfig
from src.infrastructure.crawler.scrapy_crawler_executor import (
    ScrapyCrawlerExecutor,
)
import pytest

def test_execute_returns_report_when_worker_succeeds(
    valid_config_data,
    tmp_path,
    monkeypatch,
):
    # Arrange: chuẩn bị config và worker giả
    config = CrawlerConfig.model_validate(valid_config_data)

    worker_path = tmp_path / "scrapy_worker.py"
    worker_path.touch()

    executor = ScrapyCrawlerExecutor(worker_path=worker_path)

    # Giả lập JSON thành công từ scrapy_worker.py
    worker_result = {
        "status": "ok",
        "crawl_run_id": "run-001",
        "items_scraped": 12,
        "requests_total": 20,
        "request_failures": 2,
        "http_responses_ignored": 1,
        "finish_reason": "finished",
    }

    completed = subprocess.CompletedProcess(
        args=["python", str(worker_path)],
        returncode=0,
        stdout=json.dumps(worker_result),
        stderr="",
    )

    run_mock = Mock(return_value=completed)
    monkeypatch.setattr(
        "src.infrastructure.crawler.scrapy_crawler_executor.subprocess.run",
        run_mock,
    )

    # Act: thực thi executor
    report = executor.execute(
        config=config,
        crawl_run_id="run-001",
    )

    # Assert: xác nhận report được tạo đúng
    assert report.items_scraped == 12
    assert report.request_failures == 2
    assert report.finish_reason == "finished"

    # Xác nhận subprocess được gọi đúng một lần
    run_mock.assert_called_once()

    # Xác nhận executor gọi đúng worker
    args, kwargs = run_mock.call_args
    assert args[0][0] == __import__("sys").executable
    assert args[0][1] == str(worker_path)
    assert kwargs["timeout"] == 1900
    assert kwargs["check"] is False
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True

    # Xác nhận payload gửi cho worker
    payload = json.loads(kwargs["input"])
    assert payload["crawl_run_id"] == "run-001"
    assert payload["closespider_timeout"] == 1800
    assert payload["config_json"] == config.model_dump_json()

def test_execute_raises_when_worker_returns_nonzero_exit_code(
    valid_config_data,
    tmp_path,
    monkeypatch,
):
    config = CrawlerConfig.model_validate(valid_config_data)

    worker_path = tmp_path / "scrapy_worker.py"
    worker_path.touch()

    executor = ScrapyCrawlerExecutor(worker_path=worker_path)

    completed = subprocess.CompletedProcess(
        args=["python", str(worker_path)],
        returncode=1,
        stdout="",
        stderr="worker failed",
    )

    run_mock = Mock(return_value=completed)
    monkeypatch.setattr(
        "src.infrastructure.crawler.scrapy_crawler_executor.subprocess.run",
        run_mock,
    )

    with pytest.raises(RuntimeError, match="Scrapy worker failed"):
        executor.execute(config, "run-001")

    run_mock.assert_called_once()

