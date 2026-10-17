from datetime import datetime, timezone
from unittest.mock import Mock
from src.application.crawler.crawl_run_result import CrawlStatus
from src.application.crawler.crawler_runner import CrawlerRunner
from src.application.crawler.crawler_executor import CrawlExecutionReport
from src.domain.entities.crawler_config import CrawlerConfig

def test_runner_records_timestamps_in_execution_order(valid_config_data):
    config = CrawlerConfig(**valid_config_data)

    started_at = datetime(
        2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc
    )
    finished_at = datetime(
        2026, 1, 1, 10, 1, 0, tzinfo=timezone.utc
    )

    events = []

    def clock_side_effect():
        events.append("clock")
        return [started_at, finished_at][events.count("clock") - 1]

    def execute_side_effect(*, config, crawl_run_id):
        events.append("execute")
        return CrawlExecutionReport(
            items_scraped=1,
            finish_reason="finished",
            request_failures=0,
        )

    clock = Mock(side_effect=clock_side_effect)
    executor = Mock()
    executor.execute.side_effect = execute_side_effect

    runner = CrawlerRunner(
        executor=executor,
        clock=clock,
        run_id_factory=Mock(return_value="crawl-run-006"),
    )

    result = runner.run(config)

    assert result.started_at == started_at
    assert result.finished_at == finished_at

    assert events == ["clock", "execute", "clock"]
    assert clock.call_count == 2
    executor.execute.assert_called_once_with(
        config=config,
        crawl_run_id="crawl-run-006",
    )

    assert result.status == CrawlStatus.SUCCESS
