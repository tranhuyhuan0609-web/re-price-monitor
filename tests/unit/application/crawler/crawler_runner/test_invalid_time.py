from src.application.crawler.crawl_run_result import (
    CrawlRunResult,
    CrawlStatus,
)
import pytest
from src.application.crawler.crawler_runner import CrawlerRunner
from src.domain.entities.crawler_config import CrawlerConfig
from src.application.crawler.crawler_executor import (
    CrawlExecutionReport,
)
from unittest.mock import Mock
from datetime import datetime, timezone
def test_runner_with_invalid_time_raises_type_error(valid_config_data):
    # Arrange
    config = CrawlerConfig(**valid_config_data)

    started_at = datetime(2026, 1, 1, 10, 4, tzinfo=timezone.utc)
    finished_at = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)
    clock = Mock(side_effect=[started_at, finished_at])  # Invalid time values
    run_id_factory = Mock(return_value="crawl-run-001")
    executor = Mock()

    runner = CrawlerRunner(
        executor=executor,
        clock=clock,
        run_id_factory=run_id_factory,
    )

    with pytest.raises(ValueError) as exc_info:
        # Act
        runner.run(config)

    # Assert
    assert str(exc_info.value) == "finished_at must not precede started_at"
    assert executor.execute.call_count == 1