from unittest.mock import Mock
from src.infrastructure.crawler.spiders.real_estate_spider import RealEstateSpider
from src.domain.entities.crawler_config import CrawlerConfig
from scrapy.http import HtmlResponse, Request
from src.domain.entities.raw_event import RawEventBuildError
from scrapy.utils.test import get_crawler
from scrapy.statscollectors import MemoryStatsCollector
def test_spider_continues_when_one_listing_fails_to_build(
    valid_config_data,
):
    config = CrawlerConfig(**valid_config_data)

    builder = Mock()
    builder.build.side_effect = [
        RawEventBuildError("Invalid listing"),
        Mock(),
    ]

    crawler = get_crawler(RealEstateSpider)
    spider = RealEstateSpider.from_crawler(
        crawler,
        config=config,
        crawl_run_id="run-test-001",
        event_builder=builder,
    )
    crawler.stats = MemoryStatsCollector(crawler)

    html = """
    <div class="listing">
      <a class="detail-link" href="/property/1">Listing 1</a>
    </div>
    <div class="listing">
      <a class="detail-link" href="/property/2">Listing 2</a>
    </div>
    """

    request = Request(url="https://example.com/buy")
    response = HtmlResponse(
        url=request.url,
        request=request,
        body=html.encode("utf-8"),
        encoding="utf-8",
    )

    results = list(spider.parse(response))

    assert len(results) == 1
    assert builder.build.call_count == 2
    assert crawler.stats.get_value("listing/rejected") == 1
    assert crawler.stats.get_value("listing/events") == 1