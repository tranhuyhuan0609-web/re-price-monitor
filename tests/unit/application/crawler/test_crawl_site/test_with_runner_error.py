from src.application.interfaces.config_repository import ConfigRepository
from src.application.crawler.crawler_runner import CrawlerRunner
from src.application.crawler.crawl_run_result import CrawlRunResult
from src.application.crawler.crawl_site import CrawlSite
from src.domain.entities.crawler_config import CrawlerConfig
import pytest
from unittest.mock import Mock
async def test_execute_with_runner_error(valid_config_data):
    # Create a mock ConfigRepository
    config = CrawlerConfig(**valid_config_data)
    mock_config_repository = Mock(spec=ConfigRepository)
    mock_config_repository.get_config.return_value = config

    # Create a mock CrawlerRunner that raises an exception
    mock_runner = Mock(spec=CrawlerRunner)
    mock_runner.run.side_effect = RuntimeError("Crawler runner error")

    # Create an instance of CrawlSite with the mocked dependencies
    crawl_site = CrawlSite(
        config_repository=mock_config_repository,
        runner=mock_runner,
    )

    # Use pytest.raises to check for the expected exception
    with pytest.raises(RuntimeError, match="Crawler runner error"):
        await crawl_site.execute("test_site_id")

    assert mock_runner.run.call_count == 1  # Ensure that the runner's run method was called once
    assert mock_config_repository.get_config.call_count == 1  # Ensure that get_config was called once