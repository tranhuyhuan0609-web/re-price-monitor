import pytest
from unittest.mock import Mock
from src.application.crawler.crawl_site import CrawlSite
from src.application.interfaces.config_repository import ConfigRepository
from src.application.crawler.crawler_runner import CrawlerRunner
from src.application.exceptions.config_exceptions import ConfigNotFoundError
@pytest.mark.parametrize(
    "site_id",
    [
        "",
        "   ",
        None,
        123,
    ],
)
async def test_execute_rejects_invalid_site_id(site_id):
    # Arrange
    repository = Mock(spec=ConfigRepository)
    runner = Mock(spec=CrawlerRunner)

    use_case = CrawlSite(
        config_repository=repository,
        runner=runner,
    )

    # Act & Assert
    with pytest.raises(ValueError, match="site_id must not be blank"):
        await use_case.execute(site_id)

    repository.get_config.assert_not_called()
    runner.run.assert_not_called()
   