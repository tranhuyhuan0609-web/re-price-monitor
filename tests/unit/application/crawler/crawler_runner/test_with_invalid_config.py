from src.application.crawler.crawl_run_result import (
    CrawlRunResult,
    CrawlStatus,
)
from src.application.crawler.crawler_runner import CrawlerRunner
from src.domain.entities.crawler_config import CrawlerConfig
from src.application.crawler.crawler_executor import (
    CrawlExecutionReport,
)
from unittest.mock import Mock
import pytest
from datetime import datetime, timezone
def test_runner_with_invalid_config_raises_type_error():
    # Arrange
    invalid_config = "not a CrawlerConfig"

    clock = Mock()
    run_id_factory = Mock(return_value="crawl-run-001")
    executor = Mock()

    runner = CrawlerRunner(
        executor=executor,
        clock=clock,
        run_id_factory=run_id_factory,
    )

    with pytest.raises(TypeError) as exc_info:
        # Act
        runner.run(invalid_config)

    # Assert
    assert str(exc_info.value) == "config must be a CrawlerConfig"
    assert executor.execute.call_count == 0