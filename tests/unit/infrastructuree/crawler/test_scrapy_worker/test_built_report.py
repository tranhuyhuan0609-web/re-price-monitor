from src.infrastructure.crawler import scrapy_worker
def test_build_report_returns_expected_values():
    # Arrange
    stats = {
    "item_scraped_count": 12,
    "downloader/request_count": 20,
    "request/failed": 2,
    "httperror/response_ignored_count": 1,
    "finish_reason": "finished",
}
    crawl_run_id = "run-001" 
    # Act
    report = scrapy_worker._build_report(stats, crawl_run_id)

    # Assert
    assert report == {
        "status": "ok",
        "crawl_run_id": "run-001",
        "items_scraped": 12,
        "requests_total": 20,
        "request_failures": 2,
        "http_responses_ignored": 1,
        "finish_reason": "finished",
    }
def test_build_report_with_missing_stats():
    stats = {}
    crawl_run_id = "run-002"
    report = scrapy_worker._build_report(stats, crawl_run_id)
    assert report == {
        "status": "ok",
        "crawl_run_id": "run-002",
        "items_scraped": 0,
        "requests_total": 0,
        "request_failures": 0,
        "http_responses_ignored": 0,
        "finish_reason": None,
    }
