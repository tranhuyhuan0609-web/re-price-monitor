from src.domain.entities.crawler_config import CrawlerConfig
from src.infrastructure.crawler.spiders.real_estate_spider import RealEstateSpider
from scrapy.http import HtmlResponse, Request
from scrapy.statscollectors import MemoryStatsCollector
from unittest.mock import Mock
from scrapy.utils.test import get_crawler
def test_spider_not_schedule_seen_pages(valid_config_data):
    config = CrawlerConfig(**valid_config_data)
    builder = Mock()
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
          <a class="detail-link" href="/property/123">
            Can ho Ha Noi
          </a>
        </div>
        <a class="next" href="/buy">Next</a>
      </body>
    </html>
    """
    request = Mock()
    request.url = "https://example.com/buy"
    response = HtmlResponse(
        url=request.url,
        request=request,
        body=html.encode("utf-8"),
        encoding="utf-8",
    )
    parse_results = list(spider.parse(response))
    assert len(parse_results) == 1
    assert not any(isinstance(result, Request) for result in parse_results)