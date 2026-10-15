from src.domain.entities.crawler_config import CrawlerConfig
from pydantic import ValidationError
import pytest
def test_two_start_urls_with_same_domain_are_valid(valid_config_data):
    valid_config_data["start_urls"] = ["https://example.com/page1", "https://example.com/page2"]
    config = CrawlerConfig(**valid_config_data)
    assert len(config.start_urls) == 2
def test_start_url_domain_must_be_in_allowed_domains(valid_config_data):
    valid_config_data["start_urls"] = ["https://not-allowed.com/page1"]
    with pytest.raises(ValidationError):
        CrawlerConfig(**valid_config_data)
def test_two_same_start_urls_from_same_domains_are_invalid(valid_config_data):
    valid_config_data["start_urls"] = ["https://example.com/page1", "https://example.com/page1"]
    with pytest.raises(ValidationError):
        CrawlerConfig(**valid_config_data)
def test_with_none_start_urls_is_invalid(valid_config_data):
    valid_config_data["start_urls"] = []
    with pytest.raises(ValidationError):
        CrawlerConfig(**valid_config_data)
def test_start_urls_exceed_max_pages_is_invalid(valid_config_data):
    valid_config_data["start_urls"] = [
        "https://example.com/page1",
        "https://example.com/page2",
        "https://example.com/page3",
    ]
    valid_config_data["pagination"]["max_pages"] = 2
    with pytest.raises(ValidationError):
        CrawlerConfig(**valid_config_data)