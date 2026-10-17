from src.application.crawler.crawl_run_result import (
    CrawlRunResult,
    CrawlStatus,
)
from src.application.crawler.crawler_runner import CrawlerRunner
from src.domain.entities.crawler_config import CrawlerConfig
from src.application.crawler.crawler_executor import (
    CrawlExecutionReport,
)
from datetime import datetime, timezone
from unittest.mock import Mock, patch
def test_runner_returns_failed_when_crawl_raises_exception(valid_config_data):
    # Arrange
    config = CrawlerConfig(**valid_config_data)

    started_at = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    finished_at = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)

    clock = Mock(side_effect=[started_at, finished_at])
    run_id_factory = Mock(return_value="crawl-run-003")

    executor = Mock()
    executor.execute.side_effect = RuntimeError("Simulated crawl failure")

    runner = CrawlerRunner(
        executor=executor,
        clock=clock,
        run_id_factory=run_id_factory,
    )

    # Act
    with patch("src.application.crawler.crawler_runner.logger") as mock_logger:
        result = runner.run(config)

    # Assert
    assert isinstance(result, CrawlRunResult)
    assert result.crawl_run_id == "crawl-run-003"
    assert result.status == CrawlStatus.FAILED
    assert result.error.startswith("RuntimeError: Simulated crawl failure")
    assert result.started_at == started_at
    assert result.finished_at == finished_at

    executor.execute.assert_called_once_with(
        config=config,
        crawl_run_id="crawl-run-003",
    )
    run_id_factory.assert_called_once_with()
    assert clock.call_count == 2
    mock_logger.exception.assert_called_once()

import pytest
from datetime import datetime, timezone

from src.application.crawler.crawl_run_result import (
    CrawlRunResult,
    CrawlStatus,
)


def test_failed_crawl_without_error_raises_value_error():
    started_at = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    finished_at = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)

    with pytest.raises(
        ValueError,
        match="failed crawl must contain an error",
    ):
        CrawlRunResult(
            crawl_run_id="crawl-run-010",
            status=CrawlStatus.FAILED,
            started_at=started_at,
            finished_at=finished_at,
            error=None,
        )

    