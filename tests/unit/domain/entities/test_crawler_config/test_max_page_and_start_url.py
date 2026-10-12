from src.domain.entities.crawler_config import CrawlerConfig
from pydantic import HttpUrl, ValidationError
import pytest
def test_valid_max_page_and_start_url(valid_config_data):
    valid_config_data["pagination"]["max_pages"] = 2
    valid_config_data["start_urls"] = ["https://example.com/page1", "https://example.com/page2"]
    config = CrawlerConfig(**valid_config_data)
    assert config.pagination.max_pages == 2
    assert config.start_urls == [HttpUrl("https://example.com/page1"), HttpUrl("https://example.com/page2")]
def test_invalid_max_page_and_start_url(valid_config_data):
    valid_config_data["pagination"]["max_pages"] = 2
    valid_config_data["start_urls"] = ["https://example.com/page1", "https://example.com/page2", "https://example.com/page3"]
    with pytest.raises(ValidationError):
        CrawlerConfig(**valid_config_data)