from __future__ import annotations

import asyncio

from psycopg_pool import AsyncConnectionPool

from src.application.crawler.crawl_site import CrawlSite
from src.application.crawler.crawler_runner import CrawlerRunner
from src.application.crawler.crawler_scheduler import CrawlerScheduler
from src.infrastructure.database.postgres_config_repository import (
    PostgresConfigRepository,
)


async def run_scheduler(
    *,
    pool: AsyncConnectionPool,
    runner: CrawlerRunner,
    interval_seconds: float = 300.0,
    max_concurrency: int = 1,
) -> None:
    repository = PostgresConfigRepository(pool)
    crawl_site = CrawlSite(repository, runner)

    scheduler = CrawlerScheduler(
        config_repository=repository,
        run_site=lambda config: crawl_site.execute(config.site_id),
        interval_seconds=interval_seconds,
        max_concurrency=max_concurrency,
    )
    await scheduler.run_forever()


def run_scheduler_until_cancelled(**kwargs) -> None:
    try:
        asyncio.run(run_scheduler(**kwargs))
    except KeyboardInterrupt:
        return
