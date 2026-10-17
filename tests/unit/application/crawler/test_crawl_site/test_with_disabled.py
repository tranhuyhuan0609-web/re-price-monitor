from src.application.interfaces.config_repository import ConfigRepository
from src.application.crawler.crawler_runner import CrawlerRunner
from src.application.crawler.crawl_run_result import CrawlRunResult
from src.application.crawler.crawl_site import CrawlSite
import pytest

from unittest.mock import Mock

from src.domain.entities.crawler_config import CrawlerConfig
async def test_execute_with_disabled_site(valid_config_data):
    # Create a mock ConfigRepository
    valid_config_data["enabled"] = False  # Set the enabled attribute to False
    config = CrawlerConfig(**valid_config_data)
    mock_config_repository = Mock(spec=ConfigRepository)
    mock_config_repository.get_config.return_value = config

    # Create a mock CrawlerRunner
    mock_runner = Mock(spec=CrawlerRunner)

    # Create an instance of CrawlSite with the mocked dependencies
    crawl_site = CrawlSite(
        config_repository=mock_config_repository,
        runner=mock_runner,
    )

    # Use pytest.raises to check for the expected ValueError
    with pytest.raises(ValueError,match = "Crawler for site 'test_site_id' is disabled."):
        await crawl_site.execute("test_site_id")
    assert mock_runner.run.call_count == 0  # Ensure that the runner's run method was not called
    assert mock_config_repository.get_config.call_count == 1  # Ensure that get_config was called once