import pytest

from src.domain.entities.crawler_config import (
    CrawlerConfig,
    CrawlerSettings,
    Pagination,
    ProxySettings,
    Selectors,
)


def test_valid_config_can_be_created(valid_config_data):
    config = CrawlerConfig(**valid_config_data)

    assert isinstance(config, CrawlerConfig)
    assert config.site_id == "batdongsan"
    assert config.name == "Bat Dong San"
    assert config.enabled is True
    assert str(config.base_url) == "https://example.com/"
    assert len(config.start_urls) == 1


def test_nested_models_are_validated(valid_config_data):
    config = CrawlerConfig(**valid_config_data)

    assert isinstance(config.selectors, Selectors)
    assert isinstance(config.pagination, Pagination)
    assert isinstance(config.crawler_settings, CrawlerSettings)
    assert isinstance(config.proxy_settings, ProxySettings)


def test_default_proxy_settings_are_disabled(valid_config_data):
    config = CrawlerConfig(**valid_config_data)

    assert config.proxy_settings.enabled is False
    assert config.proxy_settings.rotation_enabled is False
    assert config.proxy_settings.proxies == []
    assert config.proxy_settings.max_failures == 3
    assert config.proxy_settings.cooldown_seconds == 60