from src.domain.entities.raw_event import RawEvent
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import Mock
from datetime import datetime, timezone

import pytest
import pytest_twisted
from scrapy import signals
from scrapy.crawler import CrawlerRunner
from scrapy.settings import Settings

from src.domain.entities.crawler_config import CrawlerConfig
from src.infrastructure.crawler.spiders.real_estate_spider import (
    RealEstateSpider,
)

class ListingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"""
        <html>
          <body>
            <div class="listing">
              <a class="detail-link" href="/property/123">
                Can ho Ha Noi
              </a>
            </div>
          </body>
        </html>
        """
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass

@pytest.mark.filterwarnings("ignore::DeprecationWarning")
@pytest_twisted.inlineCallbacks
def test_scrapy_runtime_accepts_raw_event(
    valid_config_data,
):
    server = HTTPServer(("127.0.0.1", 0), ListingHandler)
    server_thread = Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        host, port = server.server_address
        config_data = {
            **valid_config_data,
            "base_url": f"http://{host}:{port}",
            "start_urls": [f"http://{host}:{port}/buy"],
            "allowed_domains": [host],
        }

        config = CrawlerConfig(**config_data)
        raw_event = {
                            "raw_event_id": "event-001",
                            "source": "example",
                            "url": "https://example.com/listing/123",
                            "crawl_run_id": "run-001",
                            "crawled_at": datetime(2026, 1, 1, 2, 0, 0, tzinfo=timezone.utc),
                            "parser_version": "1.0.0",
                            "raw_payload": {"listing": {"price": 100}}
        }
        event_builder = Mock()
        event_builder.build.return_value =  RawEvent(
               **raw_event
                )

        settings = Settings({
            "LOG_ENABLED": False,
            "ROBOTSTXT_OBEY": False,
            "RETRY_ENABLED": False,
            "DOWNLOAD_TIMEOUT": 5,
            "TWISTED_REACTOR": "twisted.internet.selectreactor.SelectReactor",
            "REMOTE_CONTROL_ENABLED": False,
        })

        runner = CrawlerRunner(settings)
        crawler = runner.create_crawler(RealEstateSpider)

        scraped_items = []
        spider_stats = {}

        def collect_item(item, response, spider):
            scraped_items.append(item)

        def spider_closed(spider, reason):
            spider_stats.update(spider.crawler.stats.get_stats())
        crawler.signals.connect(
            collect_item,
            signal=signals.item_scraped,
)

        crawler.signals.connect(
            spider_closed,
            signal=signals.spider_closed,
)

        # Await trực tiếp quá trình crawl (chạy bất đồng bộ thực sự)
        yield runner.crawl(
            crawler,
            config=config,
            crawl_run_id="run-runtime-test",
            event_builder=event_builder,
        )
        print("SCRAPED ITEMS:", scraped_items)
        print("BUILDER CALL COUNT:", event_builder.build.call_count)
        print("SPIDER STATS:", spider_stats)

        # Các khẳng định (assertions) bây giờ sẽ chạy ĐÚNG THỜI ĐIỂM sau khi crawl xong
        assert len(scraped_items) == 1
        event_builder.build.assert_called_once()
        assert isinstance(scraped_items[0], RawEvent)
        assert scraped_items[0].raw_event_id == "event-001"
    
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=2)
