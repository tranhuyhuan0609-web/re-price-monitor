
from src.domain.entities.crawler_config import CrawlerConfig
from src.application.parsers.listings_parser import ListingParser


def test_crawler_config_can_initialize_listing_parser(
    valid_config_data,
):
    config = CrawlerConfig(**valid_config_data)
    parser = ListingParser(
        source=config.site_id,
        selectors=config.selectors.to_parser_dict(),
        allowed_domains=config.allowed_domains,
    )

    assert parser is not None
    assert parser.source == config.site_id
