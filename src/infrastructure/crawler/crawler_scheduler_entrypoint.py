from __future__ import annotations

import asyncio

from psycopg import connect
from psycopg_pool import AsyncConnectionPool

from src.application.crawler.crawler_runner import CrawlerRunner
from src.infrastructure.config.settings import load_settings
from src.infrastructure.crawler.postgres_scheduler_service import run_scheduler
from src.infrastructure.crawler.scrapy_crawler_executor import (
    ScrapyCrawlerExecutor,
)
from src.infrastructure.postgres.crawl_run_recorder import (
    PostgresCrawlRunRecorder,
)


async def main() -> None:
    settings = load_settings()
    pool = AsyncConnectionPool(
        conninfo=settings.postgres_dsn,
        min_size=1,
        max_size=4,
        open=False,
    )
    await pool.open()
    await pool.wait()
    try:
        with connect(settings.postgres_dsn, autocommit=True) as connection:
            runner = CrawlerRunner(
                ScrapyCrawlerExecutor(
                    timeout_seconds=1900,
                    closespider_timeout=1800,
                ),
                recorder=PostgresCrawlRunRecorder(connection),
            )
            await run_scheduler(
                pool=pool,
                runner=runner,
                interval_seconds=300.0,
                max_concurrency=1,
            )
    finally:
        await pool.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
