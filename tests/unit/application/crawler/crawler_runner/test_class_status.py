import pytest

from src.application.crawler.crawl_run_result import CrawlStatus
from src.application.crawler.crawler_executor import CrawlExecutionReport
from src.application.crawler.crawler_runner import _classify_status


@pytest.mark.parametrize(
    ("finish_reason", "request_failures", "expected_status"),
    [
        ("finished", 0, CrawlStatus.SUCCESS),
        ("finished", 1, CrawlStatus.PARTIAL),
        ("finished", 3, CrawlStatus.PARTIAL),
        ("closespider_timeout", 0, CrawlStatus.PARTIAL),
        (None, 0, CrawlStatus.PARTIAL),
    ],
)
def test_classify_status(
    finish_reason,
    request_failures,
    expected_status,
):
    report = CrawlExecutionReport(
        items_scraped=10,
        finish_reason=finish_reason,
        request_failures=request_failures,
    )

    result = _classify_status(report)

    assert result is expected_status