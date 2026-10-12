import pytest
from pydantic import ValidationError

from src.domain.entities.crawler_config import CrawlerSettings, CrawlerConfig
def test_crawler_settings_rejects_unknown_field():
    with pytest.raises(ValidationError):
        CrawlerSettings(unknown_option=True)


def test_crawler_config_rejects_unknown_field(valid_config_data):
    data = valid_config_data.copy()
    data["unknown_option"] = True

    with pytest.raises(ValidationError):
        CrawlerConfig(**data)