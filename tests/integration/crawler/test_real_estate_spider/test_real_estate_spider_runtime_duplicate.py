
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from unittest.mock import Mock
import pytest
import pytest_twisted
from scrapy import signals
from scrapy.crawler import CrawlerRunner
from scrapy.settings import Settings
from src.domain.entities.raw_event import RawEventBuilder
from src.domain.entities.raw_event import RawEvent
from src.domain.entities.crawler_config import CrawlerConfig
from src.infrastructure.crawler.spiders.real_estate_spider import RealEstateSpider
class DuplicateListingPagesHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/buy"):
            next_link = (
                '<a class="next" href="/page/2">Next</a>'
            )
        else:
            next_link = ""

        body = f"""
        <html>
            <body>
                <div class="listing">
                    <a class="detail-link"
                       href="/property/123">Same property</a>
                </div>
                {next_link}
            </body>
        </html>
        """.encode("utf-8")

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8",
        )
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


@pytest_twisted.inlineCallbacks
def test_spider_emits_duplicate_listing_from_different_pages(
    valid_config_data,
):
    server = HTTPServer(
        ("127.0.0.1", 0),
        DuplicateListingPagesHandler,
    )
    host, port = server.server_address
    base_url = f"http://{host}:{port}"

    thread = Thread(
        target=server.serve_forever,
        daemon=True,
    )
    thread.start()

    try:
        config_data = {
            **valid_config_data,
            "base_url": base_url,
            "start_urls": [f"{base_url}/buy"],
            "allowed_domains": ["127.0.0.1"],
        }
        config = CrawlerConfig.model_validate(config_data)

        event_builder = Mock(spec=RawEventBuilder)
        event_builder.build.return_value = RawEvent(
            raw_event_id="event-001",
            source=config.site_id,
            url=f"{base_url}/property/123",
            crawl_run_id="run-001",
            crawled_at=datetime(
                2026, 1, 1, tzinfo=timezone.utc
            ),
            parser_version=config.parser_version,
        )

        scraped_items = []
        spider_stats = {}

        settings = Settings({
            "LOG_ENABLED": False,
            "ROBOTSTXT_OBEY": False,
            "RETRY_ENABLED": False,
            "DOWNLOAD_TIMEOUT": 5,
            "TWISTED_REACTOR": (
                "twisted.internet.selectreactor.SelectReactor"
            ),
            "REMOTE_CONTROL_ENABLED": False,
        })

        runner = CrawlerRunner(settings)
        crawler = runner.create_crawler(RealEstateSpider)

        def on_item_scraped(item, response, spider):
            scraped_items.append(item)

        crawler.signals.connect(
          on_item_scraped,
           signal=signals.item_scraped,
)

        def on_spider_closed(spider, reason):
            spider_stats.update(
                crawler.stats.get_stats()
            )

        crawler.signals.connect(
            on_spider_closed,
            signal=signals.spider_closed,
        )

        yield runner.crawl(
            crawler,
            config=config,
            crawl_run_id="run-001",
            event_builder=event_builder,
        )
        print("BUILD CALL COUNT:", event_builder.build.call_count)
        print("SCRAPED ITEMS:", len(scraped_items))
        print("BUILD CALLS:", event_builder.build.call_args_list)
        print("SPIDER STATS:", spider_stats)
        assert event_builder.build.call_count == 1
        assert len(scraped_items) == 1
        assert spider_stats.get("listing/duplicate_listing_key") == 1

    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)