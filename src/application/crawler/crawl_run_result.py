from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class CrawlStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class CrawlRunResult:
    crawl_run_id: str
    status: CrawlStatus
    started_at: datetime
    finished_at: datetime
    error: str | None = None

    def __post_init__(self) -> None:
        if not self.crawl_run_id.strip():
            raise ValueError("crawl_run_id must not be blank")

        if self.finished_at < self.started_at:
            raise ValueError("finished_at must not precede started_at")

        if self.status is CrawlStatus.FAILED and not self.error:
            raise ValueError("failed crawl must contain an error")

        if self.status is not CrawlStatus.FAILED and self.error is not None:
            raise ValueError(
                "only failed crawl may contain an error"
            )