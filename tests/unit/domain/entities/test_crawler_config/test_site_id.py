from src.domain.entities.crawler_config import CrawlerConfig
from pydantic import ValidationError
import pytest
def test_valid_site_id(valid_config_data):
    config = CrawlerConfig(**valid_config_data)
    assert config.site_id == "batdongsan"
def test_invalid_site_id(valid_config_data):
    config = {**valid_config_data, "site_id": "Invalid Site ID!"}
    with pytest.raises(ValidationError):
        CrawlerConfig(**config)
def test_valid_name(valid_config_data):
    valid_config_data["site_id"] = "BATDONGSAN"
    config = CrawlerConfig(**valid_config_data)
    assert config.site_id == "batdongsan"