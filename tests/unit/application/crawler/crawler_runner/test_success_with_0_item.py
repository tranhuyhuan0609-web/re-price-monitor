
from datetime import datetime, timezone
from unittest.mock import Mock

from src.application.crawler.crawl_run_result import (
    CrawlRunResult,
    CrawlStatus,
)
from src.application.crawler.crawler_executor import (
    CrawlExecutionReport,
)
from src.application.crawler.crawler_runner import CrawlerRunner
from src.domain.entities.crawler_config import CrawlerConfig


def test_runner_returns_success_when_crawl_finishes_with_no_items(
    valid_config_data,
):
    # Arrange
    config = CrawlerConfig(**valid_config_data)

    started_at = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    finished_at = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)

    clock = Mock(side_effect=[started_at, finished_at])
    run_id_factory = Mock(return_value="crawl-run-001")

    executor = Mock()
    executor.execute.return_value = CrawlExecutionReport(
        items_scraped=0,
        finish_reason="finished",
        request_failures=0,
    )

    runner = CrawlerRunner(
        executor=executor,
        clock=clock,
        run_id_factory=run_id_factory,
    )

    # Act
    result = runner.run(config)

    # Assert
    assert isinstance(result, CrawlRunResult)
    assert result.crawl_run_id == "crawl-run-001"
    assert result.status == CrawlStatus.SUCCESS
    assert result.error is None
    assert result.started_at == started_at
    assert result.finished_at == finished_at

    executor.execute.assert_called_once_with(
        config=config,
        crawl_run_id="crawl-run-001",
    )
    run_id_factory.assert_called_once_with()
    assert clock.call_count == 2
