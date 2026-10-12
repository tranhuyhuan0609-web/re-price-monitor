from src.domain.entities.crawler_config import ProxySettings
from pydantic import ValidationError
import pytest
def test_proxy_repr_does_not_expose_credentials():
    proxy_url = "http://user:secret@127.0.0.1:8080"

    settings = ProxySettings(
        enabled=True,
        proxies=[proxy_url],
    )

    result = repr(settings)

    assert "user" not in result
    assert "secret" not in result
    assert proxy_url not in result


def test_proxy_str_does_not_expose_credentials():
    proxy_url = "http://user:secret@127.0.0.1:8080"

    settings = ProxySettings(
        enabled=True,
        proxies=[proxy_url],
    )

    result = str(settings)

    assert "user" not in result
    assert "secret" not in result
    assert proxy_url not in result


def test_proxy_url_is_preserved_for_crawler():
    proxy_url = "http://user:secret@127.0.0.1:8080"

    settings = ProxySettings(
        enabled=True,
        proxies=[proxy_url],
    )

    assert settings.proxies == [proxy_url]