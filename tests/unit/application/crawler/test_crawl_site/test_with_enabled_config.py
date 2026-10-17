from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from src.application.crawler.crawl_run_result import (
    CrawlRunResult,
    CrawlStatus,
)
from src.application.crawler.crawl_site import CrawlSite
from src.application.crawler.crawler_runner import CrawlerRunner
from src.application.interfaces.config_repository import ConfigRepository
from src.domain.entities.crawler_config import CrawlerConfig


@pytest.mark.asyncio
async def test_execute_runs_enabled_crawler(
    valid_config_data,
):
    # Arrange
    valid_config_data["enabled"] = True
    config = CrawlerConfig(**valid_config_data)

    expected_result = CrawlRunResult(
        crawl_run_id="crawl-run-001",
        status=CrawlStatus.SUCCESS,
        started_at=datetime(2026, 10, 17, 1, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 10, 17, 1, 1, tzinfo=timezone.utc),
    )

    repository = Mock(spec=ConfigRepository)
    repository.get_config.return_value = config

    runner = Mock(spec=CrawlerRunner)
    runner.run.return_value = expected_result

    use_case = CrawlSite(
        config_repository=repository,
        runner=runner,
    )

    # Act
    result = await use_case.execute(config.site_id)

    # Assert
    assert result is expected_result

    repository.get_config.assert_awaited_once_with(config.site_id)
    runner.run.assert_called_once_with(config)