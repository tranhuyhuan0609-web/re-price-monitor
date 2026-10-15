
from collections import Counter
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from unittest.mock import Mock
from urllib.parse import urlsplit

import pytest
import pytest_twisted
from scrapy import signals
from scrapy.crawler import CrawlerRunner
from scrapy.settings import Settings

from src.domain.entities.crawler_config import CrawlerConfig
from src.domain.entities.raw_event import RawEvent, RawEventBuildError
from src.infrastructure.crawler.spiders.real_estate_spider import (
    RealEstateSpider,
)


# ============================================================
# 1. HTTP server giả lập website bất động sản
# ============================================================

class TwoListingsHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        path = urlsplit(self.path).path

        if path == "/page/2":
            body = """
            <html>
                <body>
                    <div class="listing">
                        <a class="detail-link"
                           href="/property/101">
                            Listing loi xuat hien lai
                        </a>
                    </div>
                </body>
            </html>
            """
        else:
            body = """
            <html>
                <body>
                    <div class="listing">
                        <a class="detail-link"
                           href="/property/101">
                            Listing loi
                        </a>
                    </div>

                    <div class="listing">
                        <a class="detail-link"
                           href="/property/102">
                            Listing hop le
                        </a>
                    </div>

                    <a class="next" href="/page/2">Next</a>
                </body>
            </html>
            """

        encoded_body = body.encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded_body)))
        self.end_headers()
        self.wfile.write(encoded_body)

    def log_message(self, format_string, *args):
        # Tắt access log của HTTP server trong lúc chạy test.
        pass


@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
@pytest_twisted.inlineCallbacks
def test_rejected_listing_is_not_built_again_on_later_page(
    valid_config_data,
):

    server = HTTPServer(("127.0.0.1", 0), TwoListingsHandler)
    host, port = server.server_address
    base_url = f"http://{host}:{port}"

    server_thread = Thread(
        target=server.serve_forever,
        daemon=True,
    )
    server_thread.start()

    runner = None

    try:
      
        config_data = {
            **valid_config_data,
            "base_url": base_url,
            "start_urls": [f"{base_url}/buy"],
            "allowed_domains": [host],
        }
        config = CrawlerConfig.model_validate(config_data)

       
        event_builder = Mock()

        def build_side_effect(
            listing,
            crawl_run_id,
            *,
            parser_version,
            crawled_at,
        ):
            if listing.url.endswith("/property/101"):
                raise RawEventBuildError(
                    "Cannot build RawEvent for listing 101"
                )

            return RawEvent(
                raw_event_id="test-event-102",
                source=listing.source,
                url=listing.url,
                crawl_run_id=crawl_run_id,
                crawled_at=crawled_at,
                parser_version=parser_version,
                title=listing.title,
            )

        event_builder.build.side_effect = build_side_effect

        settings = Settings(
            {
                "LOG_ENABLED": False,
                "ROBOTSTXT_OBEY": False,
                "RETRY_ENABLED": False,
                "DOWNLOAD_TIMEOUT": 5,
                "TWISTED_REACTOR": (
                    "twisted.internet.selectreactor.SelectReactor"
                ),
                "REMOTE_CONTROL_ENABLED": False,
            }
        )

        runner = CrawlerRunner(settings)

        scraped_items = []
        spider_stats = {}

        def on_item_scraped(item, response, spider):
            scraped_items.append(item)

        def on_spider_closed(spider, reason):
            spider_stats.update(
                spider.crawler.stats.get_stats()
            )

        crawler = runner.create_crawler(RealEstateSpider)

        crawler.signals.connect(
            on_item_scraped,
            signal=signals.item_scraped,
        )
        crawler.signals.connect(
            on_spider_closed,
            signal=signals.spider_closed,
        )

        yield runner.crawl(
            crawler,
            config=config,
            crawl_run_id="test-crawl-run",
            event_builder=event_builder,
        )
        assert event_builder.build.call_count == 2

        called_urls = [
            call.args[0].url
            for call in event_builder.build.call_args_list
        ]

        url_counts = Counter(called_urls)

        assert url_counts[f"{base_url}/property/101"] == 1
        assert url_counts[f"{base_url}/property/102"] == 1
        assert len(scraped_items) == 1
        item = scraped_items[0]
        assert isinstance(item, RawEvent)
        assert item.url == f"{base_url}/property/102"
        assert item.title == "Listing hop le"
        assert spider_stats["listing/rejected"] == 1
        assert spider_stats["listing/events"] == 1
        assert spider_stats["listing/duplicate_listing_key"] == 1

    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)