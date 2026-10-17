
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.domain.entities.crawler_config import CrawlerConfig


@dataclass(frozen=True, slots=True)
class CrawlExecutionReport:
    items_scraped: int
    finish_reason: str | None
    request_failures: int

    def __post_init__(self) -> None:
        if self.items_scraped < 0:
            raise ValueError("items_scraped must be >= 0")

        if self.request_failures < 0:
            raise ValueError("request_failures must be >= 0")


class CrawlerExecutor(Protocol):
    def execute(
        self,
        config: CrawlerConfig,
        crawl_run_id: str,
    ) -> CrawlExecutionReport:
        def __post_init__(self) -> None:
            if not crawl_run_id or not isinstance(crawl_run_id, str) or crawl_run_id.strip() == "":
                raise ValueError("crawl_run_id must be a non-empty string")
            if not isinstance(config, CrawlerConfig):
                raise TypeError("config must be a CrawlerConfig")