from datetime import datetime, timezone
from unittest.mock import Mock
from src.application.crawler.crawl_run_result import (
    CrawlRunResult,
    CrawlStatus,
)
from src.application.crawler.crawler_runner import CrawlerRunner
from src.application.crawler.crawler_executor import (
    CrawlExecutionReport,
)
from src.domain.entities.crawler_config import CrawlerConfig
def test_runner_generates_unique_run_id_for_each_run(valid_config_data):
    # Arrange
    config = CrawlerConfig(**valid_config_data)

    started_at = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    finished_at = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)

    clock = Mock(
        side_effect=[
            started_at,
            finished_at,
            started_at,
            finished_at,
        ]
    )

    run_id_factory = Mock(
        side_effect=[
            "crawl-run-004",
            "crawl-run-005",
        ]
    )

    executor = Mock()
    executor.execute.return_value = CrawlExecutionReport(
        items_scraped=1,
        finish_reason="finished",
        request_failures=0,
    )

    runner = CrawlerRunner(
        executor=executor,
        clock=clock,
        run_id_factory=run_id_factory,
    )

    # Act
    first_result = runner.run(config)
    second_result = runner.run(config)

    # Assert
    assert first_result.crawl_run_id == "crawl-run-004"
    assert second_result.crawl_run_id == "crawl-run-005"
    assert first_result.crawl_run_id != second_result.crawl_run_id

    assert first_result.status == CrawlStatus.SUCCESS
    assert second_result.status == CrawlStatus.SUCCESS

    assert executor.execute.call_count == 2
  