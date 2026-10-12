from src.domain.entities.crawler_config import ProxySettings
from pydantic import ValidationError
import pytest
def test_proxy_rotation_accepts_two_valid_proxies():
    settings = ProxySettings(
        enabled=True,
        rotation_enabled=True,
        proxies=[
            "http://127.0.0.1:8080",
            "https://127.0.0.1:8081",
        ],
    )

    assert settings.enabled is True
    assert settings.rotation_enabled is True
    assert len(settings.proxies) == 2


def test_proxy_rotation_requires_proxy_enabled():
    with pytest.raises(ValidationError):
        ProxySettings(
            enabled=False,
            rotation_enabled=True,
            proxies=[
                "http://127.0.0.1:8080",
                "http://127.0.0.1:8081",
            ],
        )


def test_proxy_rotation_requires_at_least_two_proxies():
    with pytest.raises(ValidationError):
        ProxySettings(
            enabled=True,
            rotation_enabled=True,
            proxies=["http://127.0.0.1:8080"],
        )


def test_proxy_rejects_unsupported_scheme():
    with pytest.raises(ValidationError):
        ProxySettings(
            enabled=True,
            proxies=["ftp://127.0.0.1:8080"],
        )


def test_proxy_rejects_duplicate_proxies():
    with pytest.raises(ValidationError):
        ProxySettings(
            enabled=True,
            proxies=[
                "http://127.0.0.1:8080",
                "http://127.0.0.1:8080",
            ],
        )