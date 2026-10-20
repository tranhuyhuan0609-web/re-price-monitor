from __future__ import annotations
from typing import Any
from psycopg import Connection
from src.application.crawler.crawl_run_result import CrawlRunResult


class PostgresCrawlRunRecorder:
    """Persist the final outcome and metrics of each crawl run."""

    def __init__(self, connection: Connection[Any]) -> None:
        self._connection = connection

    def record(self, *, site_id: str, result: CrawlRunResult) -> None:
        if not site_id.strip():
            raise ValueError("site_id must not be blank")
        with self._connection.transaction():
            self._connection.execute(
                """
                INSERT INTO crawl_runs (
                    crawl_run_id, site_id, status, started_at, finished_at,
                    items_scraped, request_failures, finish_reason, error
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (crawl_run_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    finished_at = EXCLUDED.finished_at,
                    items_scraped = EXCLUDED.items_scraped,
                    request_failures = EXCLUDED.request_failures,
                    finish_reason = EXCLUDED.finish_reason,
                    error = EXCLUDED.error
                """,
                (
                    result.crawl_run_id,
                    site_id.strip(),
                    result.status.value,
                    result.started_at,
                    result.finished_at,
                    result.items_scraped,
                    result.request_failures,
                    result.finish_reason,
                    result.error,
                ),
            )
