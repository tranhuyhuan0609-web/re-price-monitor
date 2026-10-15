from src.domain.entities.crawler_config import CrawlerConfig
from scrapy.crawler import CrawlerRunner
from datetime import datetime
from scrapy.utils.test import get_crawler
from unittest.mock import Mock
from scrapy.settings import Settings
from src.infrastructure.crawler.spiders.real_estate_spider import RealEstateSpider
from scrapy.http import HtmlResponse, Request
from scrapy.statscollectors import MemoryStatsCollector  

def test_spider_parse_builds_raw_event(valid_config_data):
    config = CrawlerConfig(**valid_config_data)
    event = Mock()
    builder = Mock()
    builder.build.return_value = event
    runner = CrawlerRunner(Settings())
    
    crawler = get_crawler(RealEstateSpider)
    spider = RealEstateSpider.from_crawler(
        crawler,
        config=config,
        crawl_run_id="run-test-001",
        event_builder=builder,
    )
    crawler.stats = MemoryStatsCollector(crawler)

    html = """
    <html>
      <body>
        <div class="listing">
          <a class="detail-link"
             href="/property/123">Can ho Ha Noi</a>
        </div>
      </body>
    </html>
    """

    request = Request(url="https://example.com/buy")
    response = HtmlResponse(
        url=request.url,
        request=request,
        body=html.encode("utf-8"),
        encoding="utf-8",
    )

    results = list(spider.parse(response))

    assert results[0] is event

    builder.build.assert_called_once()
    args, kwargs = builder.build.call_args
    listing = args[0]
    assert listing.url == "https://example.com/property/123"
    assert listing.title == "Can ho Ha Noi"
    assert args[1] == "run-test-001"
    assert kwargs["parser_version"] == config.parser_version
    assert isinstance(kwargs["crawled_at"], datetime)
    assert kwargs["crawled_at"].tzinfo is not None
    agrs, kwargs = builder.build.call_args
    assert agrs[1] == "run-test-001"
    assert kwargs["parser_version"] == config.parser_version
    assert isinstance(kwargs["crawled_at"], datetime)
    assert kwargs["crawled_at"].tzinfo is not None
  
