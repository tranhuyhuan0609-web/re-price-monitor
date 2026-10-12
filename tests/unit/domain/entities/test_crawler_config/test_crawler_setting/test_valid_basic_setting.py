
from src.domain.entities.crawler_config import CrawlerSettings


def test_crawler_settings_defaults():
    settings = CrawlerSettings()

    assert settings.delay == 1.0
    assert settings.randomize_delay is True
    assert settings.concurrent_requests == 1
    assert settings.download_timeout == 30.0
    assert settings.retry_enabled is True
    assert settings.max_retries == 3


def test_crawler_settings_accepts_valid_configuration():
    settings = CrawlerSettings(
        delay=2.5,
        concurrent_requests=4,
        download_timeout=60,
        retry_enabled=True,
        max_retries=5,
    )

    assert settings.delay == 2.5
    assert settings.concurrent_requests == 4
    assert settings.download_timeout == 60
    assert settings.retry_enabled is True
    assert settings.max_retries == 5


def test_crawler_settings_accepts_max_concurrent_requests():
    settings = CrawlerSettings(
        concurrent_requests=10,
    )

    assert settings.concurrent_requests == 10


def test_crawler_settings_allows_zero_retries_when_disabled():
    settings = CrawlerSettings(
        retry_enabled=False,
        max_retries=0,
    )

    assert settings.retry_enabled is False
    assert settings.max_retries == 0