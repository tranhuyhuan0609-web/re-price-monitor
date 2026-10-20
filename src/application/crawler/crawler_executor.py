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
        if (
            not isinstance(self.items_scraped, int)
            or isinstance(self.items_scraped, bool)
            or self.items_scraped < 0
        ):
            raise ValueError("items_scraped must be a non-negative integer")

        if (
            not isinstance(self.request_failures, int)
            or isinstance(self.request_failures, bool)
            or self.request_failures < 0
        ):
            raise ValueError("request_failures must be a non-negative integer")


class CrawlerExecutor(Protocol):
    def execute(
        self,
        config: CrawlerConfig,
        crawl_run_id: str,
    ) -> CrawlExecutionReport:
        ...