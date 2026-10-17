from src.application.crawler.crawler_executor import CrawlExecutionReport
import pytest
def test_crawler_executor_with_valid_value():
    # Arrange
    report = CrawlExecutionReport(
        items_scraped=10,
        finish_reason="finished",
        request_failures=0,
    )

    # Assert
    assert report.items_scraped == 10
    assert report.finish_reason == "finished"
    assert report.request_failures == 0
def test_crawler_executor_with_invalid_items_scraped():
    with pytest.raises(ValueError, match="items_scraped must be >= 0"):
        CrawlExecutionReport(
            items_scraped=-1,
            finish_reason="finished",
            request_failures=0,
        )
def test_crawler_executor_with_invalid_request_failures():
    with pytest.raises(ValueError, match="request_failures must be >= 0"):
        CrawlExecutionReport(
            items_scraped=10,
            finish_reason="finished",
            request_failures=-1,
        )