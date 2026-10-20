from __future__ import annotations
import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Awaitable
from src.application.crawler.crawl_run_result import CrawlRunResult
from src.application.interfaces.config_repository import ConfigRepository
from src.domain.entities.crawler_config import CrawlerConfig
logger = logging.getLogger(__name__)


class CrawlerScheduler:
    """Poll enabled configs and run sites with bounded concurrency."""

    def __init__(
        self,
        *,
        config_repository: ConfigRepository,
        run_site: Callable[[CrawlerConfig], Awaitable[CrawlRunResult]],
        interval_seconds: float = 300.0,
        max_concurrency: int = 1,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        if max_concurrency <= 0:
            raise ValueError("max_concurrency must be positive")

        self._config_repository = config_repository
        self._run_site = run_site
        self._interval_seconds = interval_seconds
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._in_flight: set[str] = set()
        self._last_started: dict[str, datetime] = {}
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    async def run_once(self) -> list[CrawlRunResult]:
        configs = await self._config_repository.get_enabled_configs()
        selected = [
            config for config in configs
            if config.site_id not in self._in_flight
            and self._is_due(config)
        ]
        return list(
            await asyncio.gather(
                *(self._run_one(config) for config in selected)
            )
        )

    async def _run_one(self, config: CrawlerConfig) -> CrawlRunResult:
        self._in_flight.add(config.site_id)
        self._last_started[config.site_id] = self._now()
        try:
            async with self._semaphore:
                return await self._run_site(config)
        finally:
            self._in_flight.discard(config.site_id)

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("scheduler clock must return an aware datetime")
        return value.astimezone(timezone.utc)

    def _is_due(self, config: CrawlerConfig) -> bool:
        last_started = self._last_started.get(config.site_id)
        if last_started is None:
            return True
        return self._now() >= last_started + timedelta(
            seconds=config.schedule_interval_seconds
        )

    async def run_forever(self) -> None:
        while True:
            try:
                await self.run_once()
            except Exception:
                logger.exception("Crawler scheduler tick failed")
            await asyncio.sleep(self._interval_seconds)
