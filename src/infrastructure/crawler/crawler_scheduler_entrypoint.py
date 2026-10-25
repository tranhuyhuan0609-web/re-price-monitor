from __future__ import annotations
import asyncio
from psycopg_pool import ConnectionPool 
from src.application.crawler.crawler_runner import CrawlerRunner
from src.infrastructure.config.settings import load_settings
from src.infrastructure.crawler.postgres_scheduler_service import run_scheduler
from src.infrastructure.crawler.scrapy_crawler_executor import (
    ScrapyCrawlerExecutor,
)
from src.infrastructure.postgres.crawl_run_recorder import (
    PostgresCrawlRunRecorder,
)
from psycopg_pool import AsyncConnectionPool
class ThreadSafeCrawlRunRecorder:
    def __init__(self, pool: ConnectionPool):
        self._pool = pool

    def record(self, site_id, result):  
        with self._pool.connection() as conn:
            actual_recorder = PostgresCrawlRunRecorder(conn)
            return actual_recorder.record(site_id=site_id, result=result)


async def main() -> None:
    settings = load_settings()
  
    async_pool = AsyncConnectionPool(
        conninfo=settings.postgres_dsn,
        min_size=1,
        max_size=4,
        open=False,
    )
    await async_pool.open()
    await async_pool.wait()

    sync_pool = ConnectionPool(
        conninfo=settings.postgres_dsn,
        min_size=2,
        max_size=10,
        open=True,
    )

    try:
        thread_safe_recorder = ThreadSafeCrawlRunRecorder(sync_pool)

        runner = CrawlerRunner(
            ScrapyCrawlerExecutor(
                timeout_seconds=1900,
                closespider_timeout=3600,
            ),
            recorder=thread_safe_recorder, 
        )
        

        await run_scheduler(
            pool=async_pool,
            runner=runner,
            interval_seconds=300.0,
            max_concurrency=1,
        )
    finally:
        await async_pool.close()
        sync_pool.close() 

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
