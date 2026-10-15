import pytest
from src.domain.entities.crawler_config import CrawlerConfig
from src.application.parsers.listings_parser import ListingParser
def test_with_invalid_selector(valid_config_data):
    valid_config_data["selectors"]["url"] = "a.detail-link::text"  # Invalid selector
    config = CrawlerConfig(**valid_config_data)
    with pytest.raises(ValueError):
        parser = ListingParser(
            source=config.site_id,
            selectors=config.selectors.to_parser_dict(),
            allowed_domains=config.allowed_domains,
        )

    