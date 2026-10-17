
import pytest
from unittest.mock import Mock
from src.application.crawler.crawler_runner import CrawlerRunner
from src.domain.entities.crawler_config import CrawlerConfig


@pytest.mark.parametrize("invalid_run_id", ["", "   "])
def test_runner_rejects_blank_run_id_before_execution(
    valid_config_data,
    invalid_run_id,
):
    config = CrawlerConfig(**valid_config_data)

    executor = Mock()
    runner = CrawlerRunner(
        executor=executor,
        run_id_factory=Mock(return_value=invalid_run_id),
    )

    with pytest.raises(ValueError, match="run_id_factory must be a non-empty string"):
        runner.run(config)

    executor.execute.assert_not_called()
