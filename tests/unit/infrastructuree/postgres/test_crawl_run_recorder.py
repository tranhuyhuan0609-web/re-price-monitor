from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.application.crawler.crawl_run_result import CrawlRunResult, CrawlStatus
from src.infrastructure.postgres.crawl_run_recorder import PostgresCrawlRunRecorder


def test_recorder_upserts_crawl_run():
    connection = MagicMock()
    result = CrawlRunResult(
        crawl_run_id="run-1",
        status=CrawlStatus.PARTIAL,
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        finished_at=datetime(2026, 1, 1, 0, 0, 1, tzinfo=timezone.utc),
        items_scraped=10,
        request_failures=2,
        finish_reason="finished",
    )

    PostgresCrawlRunRecorder(connection).record(
        site_id="batdongsan",
        result=result,
    )

    connection.execute.assert_called_once()
    assert "crawl_runs" in connection.execute.call_args.args[0]
