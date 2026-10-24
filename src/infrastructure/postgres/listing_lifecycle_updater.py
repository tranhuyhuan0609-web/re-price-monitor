from __future__ import annotations
import logging
import time
from collections.abc import Callable
from typing import Any
from psycopg import Connection, connect
from src.infrastructure.config.settings import load_settings

logger = logging.getLogger(__name__)
INACTIVE_AFTER_MISSES = 5


def _like_prefix(prefix: str) -> str:
    """Escape LIKE wildcards in a literal prefix and anchor it at the start."""
    escaped = (
        prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    )
    return escaped + "%"


def _apply_run(connection: Connection[Any], run: tuple) -> int:
    """Đếm một lần thiếu (missed run) cho mỗi tin đăng đang active của site mà không xuất hiện trong đợt crawl này."""
    crawl_run_id, site_id, status, started_at, finished_at = run
    if status != "success":
        return 0

    source = site_id.strip().lower()
    rows = connection.execute(
        """
        UPDATE listing_lifecycle
        SET missing_count = missing_count + 1,
            status = CASE WHEN missing_count + 1 >= %(limit)s
                          THEN 'inactive' ELSE 'active' END,
            ended_at = CASE WHEN missing_count + 1 >= %(limit)s
                            THEN %(finished_at)s ELSE NULL END,
            updated_at = now()
        WHERE status = 'active'
          AND listing_key LIKE %(pattern)s
          AND last_seen_at < %(started_at)s
        RETURNING listing_key, status
        """,
        {
            "limit": INACTIVE_AFTER_MISSES,
            "finished_at": finished_at,
            "pattern": _like_prefix(f"{source}:url:"),
            "started_at": started_at,
        },
    ).fetchall()

    ended = [row[0] for row in rows if row[1] == "inactive"]
    if ended:
        with connection.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO listing_status_event
                    (listing_key, status, occurred_at, crawl_run_id)
                VALUES (%s, 'inactive', %s, %s)
                ON CONFLICT DO NOTHING
                """,
                [(key, finished_at, crawl_run_id) for key in ended],
            )
    logger.info(
        "Run %s site=%s: %d listing(s) missed, %d became inactive",
        crawl_run_id, site_id, len(rows), len(ended),
    )
    return len(ended)


def apply_pending_runs(
    connection: Connection[Any],
    *,
    grace_seconds: int,
) -> int:
    while True:
        with connection.transaction():
            run = connection.execute(
                """
                SELECT crawl_run_id, site_id, status, started_at, finished_at
                FROM crawl_runs
                WHERE lifecycle_applied_at IS NULL
                  AND finished_at <= now() - (%s * interval '1 second')
                ORDER BY finished_at
                LIMIT 1
                FOR UPDATE SKIP LOCKED
                """,
                (grace_seconds,),
            ).fetchone()
            if run is None:
                return handled

            _apply_run(connection, run)
            connection.execute(
                "UPDATE crawl_runs SET lifecycle_applied_at = now() "
                "WHERE crawl_run_id = %s",
                (run[0],),
            )
        handled += 1


class ListingLifecycleUpdater:
   
    def __init__(
        self,
        *,
        dsn: str,
        grace_seconds: int = 600,
        interval_seconds: int = 300,
        connect_fn: Callable[[str], Connection[Any]] = connect,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if grace_seconds < 0:
            raise ValueError("grace_seconds must not be negative")
        if interval_seconds < 60:
            raise ValueError("interval_seconds must be at least 60")
        self._dsn = dsn
        self._grace_seconds = grace_seconds
        self._interval_seconds = interval_seconds
        self._connect = connect_fn
        self._sleep = sleep

    def run_once(self) -> int:
        with self._connect(self._dsn) as connection:
            return apply_pending_runs(
                connection, grace_seconds=self._grace_seconds
            )

    def run_forever(self) -> None:
        while True:
            try:
                self.run_once()
            except Exception:
                logger.exception("Listing lifecycle update failed")
            self._sleep(self._interval_seconds)


def run_listing_lifecycle_updater() -> None:
    settings = load_settings()
    ListingLifecycleUpdater(
        dsn=settings.postgres_dsn,
        grace_seconds=settings.LIFECYCLE_GRACE_SECONDS,
        interval_seconds=settings.LIFECYCLE_CHECK_INTERVAL_SECONDS,
    ).run_forever()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_listing_lifecycle_updater()
