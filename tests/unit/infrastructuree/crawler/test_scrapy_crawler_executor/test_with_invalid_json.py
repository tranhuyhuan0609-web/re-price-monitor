from src.domain.entities.crawler_config import CrawlerConfig
from src.infrastructure.crawler.scrapy_crawler_executor import ScrapyCrawlerExecutor
import subprocess
from unittest.mock import Mock
import pytest
def test_execute_raises_error_when_worker_returns_invalid_json(
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
            stdout="{invalid json}",
            stderr="",
        )
    )

    monkeypatch.setattr(
        "src.infrastructure.crawler.scrapy_crawler_executor.subprocess.run",
        run_mock,
    )

    with pytest.raises(
        RuntimeError,
        match="Scrapy worker returned invalid JSON",
    ):
        executor.execute(config, "run-001")

    run_mock.assert_called_once()

def test_execute_raises_error_when_worker_returns_non_object_json(
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
            stdout="[]",
            stderr="",
        )
    )

    monkeypatch.setattr(
        "src.infrastructure.crawler.scrapy_crawler_executor.subprocess.run",
        run_mock,
    )

    with pytest.raises(
        RuntimeError,
        match="Worker result must be a JSON object",
    ):
        executor.execute(config, "run-001")

    run_mock.assert_called_once()

