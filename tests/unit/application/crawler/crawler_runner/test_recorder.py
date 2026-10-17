from datetime import datetime, timezone
from unittest.mock import Mock

from src.application.crawler.crawler_runner import CrawlerRunner
from src.application.crawler.crawler_executor import CrawlExecutionReport
from src.domain.entities.crawler_config import CrawlerConfig


def test_runner_records_report_metrics(valid_config_data):
    valid_config = CrawlerConfig(**valid_config_data)
    recorder = Mock()
    executor = Mock()
    executor.execute.return_value = CrawlExecutionReport(
        items_scraped=12,
        finish_reason="finished",
        request_failures=1,
    )
    clock_values = iter(
        (
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 1, 0, 0, 1, tzinfo=timezone.utc),
        )
    )

    result = CrawlerRunner(
        executor,
        clock=lambda: next(clock_values),
        run_id_factory=lambda: "run-1",
        recorder=recorder,
    ).run(valid_config)

    assert result.items_scraped == 12
    assert result.request_failures == 1
    recorder.record.assert_called_once_with(
        site_id=valid_config.site_id,
        result=result,
    )
