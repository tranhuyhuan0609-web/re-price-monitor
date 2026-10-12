from src.domain.entities.crawler_config import CrawlerSettings
from pydantic import ValidationError
import pytest
def test_retry_disabled_with_zero_retries_is_valid():
    settings = CrawlerSettings(
        retry_enabled=False,
        max_retries=0,
    )

    assert settings.retry_enabled is False
    assert settings.max_retries == 0


def test_retry_disabled_with_positive_retries_is_invalid():
    with pytest.raises(ValidationError):
        CrawlerSettings(
            retry_enabled=False,
            max_retries=3,
        )


def test_retry_enabled_with_zero_retries_is_invalid():
    with pytest.raises(ValidationError):
        CrawlerSettings(
            retry_enabled=True,
            max_retries=0,
        )