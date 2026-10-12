import pytest
from pydantic import ValidationError
from src.domain.entities.crawler_config import CrawlerConfig

def test_crawler_config_defaults_to_utc(valid_config_data):
    config = CrawlerConfig(**valid_config_data)

    assert config.source_timezone == "UTC"
    assert str(config.source_zoneinfo()) == "UTC"


def test_crawler_config_accepts_valid_source_timezone(valid_config_data):
    valid_config_data["source_timezone"] = "Asia/Ho_Chi_Minh"

    config = CrawlerConfig(**valid_config_data)

    assert config.source_timezone == "Asia/Ho_Chi_Minh"
    assert config.source_zoneinfo().key == "Asia/Ho_Chi_Minh"


def test_crawler_config_rejects_unknown_source_timezone(valid_config_data):
    valid_config_data["source_timezone"] = "Invalid/Timezone"

    with pytest.raises(ValidationError):
        CrawlerConfig(**valid_config_data)