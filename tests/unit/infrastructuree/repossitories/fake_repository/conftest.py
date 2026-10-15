import pytest
from src.domain.entities.crawler_config import CrawlerConfig
from src.infrastructure.repositories.fake_config_repository import (
    FakeConfigRepository,
)


@pytest.fixture
def fake_config_repository():
    return FakeConfigRepository()


@pytest.fixture
def valid_config():
    return CrawlerConfig(
        site_id="batdongsan",
        name="Bat Dong San",
        enabled=True,
        base_url="https://example.com",
        start_urls=["https://example.com/buy"],
        allowed_domains=["example.com"],
        selectors={
            "item": ".listing",
            "url": "a.detail-link::attr(href)",
            "title": "a.detail-link::text",
        },
        pagination={
            "enabled": False,
            "max_pages": 10,
        },
        crawler_settings={},
    )
