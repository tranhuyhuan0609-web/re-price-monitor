
from pydantic import ValidationError
import pytest

from src.domain.entities.crawler_config import ProxySettings


def test_proxy_settings_defaults():
    settings = ProxySettings()

    assert settings.enabled is False
    assert settings.rotation_enabled is False
    assert settings.proxies == []
    assert settings.max_failures == 3
    assert settings.cooldown_seconds == 60


def test_proxy_settings_accepts_valid_http_proxy():
    settings = ProxySettings(
        enabled=True,
        proxies=["http://127.0.0.1:8080"],
    )

    assert settings.enabled is True
    assert settings.proxies == ["http://127.0.0.1:8080"]


def test_enabled_proxy_requires_at_least_one_proxy():
    with pytest.raises(ValidationError):
        ProxySettings(
            enabled=True,
            proxies=[],
        )


def test_proxy_rejects_missing_hostname():
    with pytest.raises(ValidationError):
        ProxySettings(
            enabled=True,
            proxies=["http://"],
        )


def test_proxy_rejects_invalid_port():
    with pytest.raises(ValidationError):
        ProxySettings(
            enabled=True,
            proxies=["http://127.0.0.1:70000"],
        )