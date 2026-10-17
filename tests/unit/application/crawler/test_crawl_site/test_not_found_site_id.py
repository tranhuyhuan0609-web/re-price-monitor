from unittest.mock import Mock

import pytest

from src.application.crawler.crawl_site import CrawlSite
from src.application.crawler.crawler_runner import CrawlerRunner
from src.application.exceptions.config_exceptions import ConfigNotFoundError
from src.application.interfaces.config_repository import ConfigRepository


@pytest.mark.asyncio
async def test_execute_propagates_config_not_found_error():
    # Arrange
    site_id = "unknown-site"

    repository = Mock(spec=ConfigRepository)
    repository.get_config.side_effect = ConfigNotFoundError(
        f"Config with site_id '{site_id}' not found."
    )

    runner = Mock(spec=CrawlerRunner)

    use_case = CrawlSite(
        config_repository=repository,
        runner=runner,
    )

    # Act & Assert
    with pytest.raises(ConfigNotFoundError, match="unknown-site"):
        await use_case.execute(site_id)

    repository.get_config.assert_awaited_once_with(site_id)
    runner.run.assert_not_called()