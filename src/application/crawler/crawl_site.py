from __future__ import annotations
import asyncio
from src.application.interfaces.config_repository import ConfigRepository
from src.application.crawler.crawler_runner import CrawlerRunner
from src.application.crawler.crawl_run_result import CrawlRunResult

class CrawlSite:
    def __init__(
        self,
        config_repository: ConfigRepository,
        runner: CrawlerRunner,
    ) -> None:
        self._config_repository = config_repository
        self._runner = runner

    async def execute(self, site_id: str) -> CrawlRunResult:
        if not isinstance(site_id, str) or not site_id.strip():
            raise ValueError("site_id must not be blank")

        config = await self._config_repository.get_config(
            site_id.strip()
        )

        if not config.enabled:
            raise ValueError(
                f"Crawler for site '{site_id}' is disabled."
            )

        return await asyncio.to_thread(
            self._runner.run,
            config,
        )
