import pytest
import pytest_twisted
from scrapy.crawler import CrawlerRunner
from scrapy import signals
from scrapy.settings import Settings
from twisted.internet import reactor
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from unittest.mock import Mock
from src.infrastructure.crawler.spiders.real_estate_spider import RealEstateSpider
from src.application.parsers.listings_parser import ParsedListing
from src.domain.entities.raw_event import RawEvent
from src.domain.entities.crawler_config import CrawlerConfig
@pytest.mark.filterwarnings(
    "ignore::pytest.PytestUnhandledThreadExceptionWarning"
)
@pytest_twisted.inlineCallbacks
def test_same_listing_is_processed_again_in_a_new_crawl_run(
    valid_config_data,
):
   
    class SingleListingHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = b"""
            <html>
                <body>
                    <div class="listing">
                        <a class="detail-link"
                           href="/property/101">
                            Listing test
                        </a>
                    </div>
                </body>
            </html>
            """

            self.send_response(200)
            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8",
            )
            self.send_header(
                "Content-Length",
                str(len(body)),
            )
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format_string, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), SingleListingHandler)
    host, port = server.server_address
    base_url = f"http://{host}:{port}"

    server_thread = Thread(
        target=server.serve_forever,
        daemon=True,
    )
    server_thread.start()

    try:
        # 1. Tạo cấu hình crawler cho website giả lập.
        config_data = {
            **valid_config_data,
            "base_url": base_url,
            "start_urls": [f"{base_url}/buy"],
            "allowed_domains": [host],
        }
        config = CrawlerConfig.model_validate(config_data)

        # 2. Tạo builder trả về RawEvent hợp lệ.
        event_builder = Mock()

        def build_side_effect(
            listing,
            crawl_run_id,
            *,
            parser_version,
            crawled_at,
        ):
            return RawEvent(
                raw_event_id=f"event-{crawl_run_id}",
                source=listing.source,
                url=listing.url,
                crawl_run_id=crawl_run_id,
                crawled_at=crawled_at,
                parser_version=parser_version,
                title=listing.title,
            )

        event_builder.build.side_effect = build_side_effect

        # 3. Cấu hình Scrapy cho integration test.
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

        # 4. Chạy crawl run thứ nhất.
        first_run_items = []

        def collect_first_item(item, response, spider):
            first_run_items.append(item)

        first_crawler = runner.create_crawler(RealEstateSpider)
        first_crawler.signals.connect(
          collect_first_item,
    signal=signals.item_scraped,
)

        yield runner.crawl(
            first_crawler,
            config=config,
            crawl_run_id="crawl-run-1",
            event_builder=event_builder,
        )

        # 5. Chạy crawl run thứ hai với cùng listing.
        second_run_items = []
        def collect_second_item(item, response, spider):
            second_run_items.append(item)
        
        second_crawler = runner.create_crawler(RealEstateSpider)
        second_crawler.signals.connect(
            collect_second_item,
            signal=signals.item_scraped,
        )
        

        yield runner.crawl(
            second_crawler,
            config=config,
            crawl_run_id="crawl-run-2",
            event_builder=event_builder,
        )

        # 6. Kiểm tra builder được gọi một lần ở mỗi run.
        assert event_builder.build.call_count == 2

        calls = event_builder.build.call_args_list

        assert calls[0].args[1] == "crawl-run-1"
        assert calls[1].args[1] == "crawl-run-2"
        
        print("First run items:", first_run_items)
        print("Second run items:", second_run_items)
        print("Builder call count:", event_builder.build.call_count)
        print("Builder calls:", event_builder.build.call_args_list)
        print("Crawler stats:", first_crawler.stats.get_stats())


        # 7. Mỗi run phải phát ra một RawEvent.
        assert len(first_run_items) == 1
        assert len(second_run_items) == 1

        first_event = first_run_items[0]
        second_event = second_run_items[0]

        assert isinstance(first_event, RawEvent)
        assert isinstance(second_event, RawEvent)

        assert first_event.url == f"{base_url}/property/101"
        assert second_event.url == f"{base_url}/property/101"

        assert first_event.crawl_run_id == "crawl-run-1"
        assert second_event.crawl_run_id == "crawl-run-2"

    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)