from src.domain.entities.crawler_config import CrawlerSettings
from pydantic import ValidationError
import pytest
def test_crawler_settings_rejects_zero_delay():
    with pytest.raises(ValidationError):
        CrawlerSettings(delay=0)


def test_crawler_settings_rejects_zero_concurrent_requests():
    with pytest.raises(ValidationError):
        CrawlerSettings(concurrent_requests=0)


def test_crawler_settings_rejects_too_many_concurrent_requests():
    with pytest.raises(ValidationError):
        CrawlerSettings(concurrent_requests=11)


def test_crawler_settings_rejects_zero_download_timeout():
    with pytest.raises(ValidationError):
        CrawlerSettings(download_timeout=0)


def test_crawler_settings_rejects_download_timeout_above_limit():
    with pytest.raises(ValidationError):
        CrawlerSettings(download_timeout=301)


def test_crawler_settings_rejects_too_many_retries():
    with pytest.raises(ValidationError):
        CrawlerSettings(
            retry_enabled=True,
            max_retries=11,
        )