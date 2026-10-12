from src.domain.entities.crawler_config import CrawlerConfig
from pydantic import ValidationError
import pytest
def test_validate_domain(valid_config_data):
    valid_config_data["allowed_domains"] = ["EXAMPLE.com"]
    config = CrawlerConfig(**valid_config_data)
    assert config.allowed_domains == ["example.com"]
def test_duplicate_domains_are_removed(valid_config_data):
    valid_config_data["allowed_domains"] = ["example.com", "EXAMPLE.com"]
    with pytest.raises(ValidationError):
        CrawlerConfig(**valid_config_data)
def test_invalid_domain_raises_validation_error(valid_config_data):
    valid_config_data["allowed_domains"] = ["http://invalid-domain.com"]
    with pytest.raises(ValidationError):
        CrawlerConfig(**valid_config_data)
def test_base_url_domain_must_be_in_allowed_domains(valid_config_data):
    valid_config_data["base_url"] = "https://not-allowed.com"
    with pytest.raises(ValidationError):
        CrawlerConfig(**valid_config_data)