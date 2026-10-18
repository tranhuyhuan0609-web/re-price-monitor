
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Protocol
from datetime import datetime, timezone
from uuid import uuid4

from src.application.crawler.crawl_run_result import (
    CrawlRunResult,
    CrawlStatus,
)
from src.application.crawler.crawler_executor import (
    CrawlExecutionReport,
    CrawlerExecutor,
)
from src.domain.entities.crawler_config import CrawlerConfig


logger = logging.getLogger(__name__)


class CrawlRunRecorder(Protocol):
    def record(
        self,
        *,
        site_id: str,
        result: CrawlRunResult,
    ) -> None:
        ...


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _new_run_id() -> str:
    return str(uuid4())


def _validate_utc_datetime(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")

    return value.astimezone(timezone.utc)


def _classify_status(report: CrawlExecutionReport) -> CrawlStatus:
    if (
        report.finish_reason != "finished"
        or report.request_failures > 0
        or report.items_scraped == 0
    ):
        return CrawlStatus.PARTIAL

    return CrawlStatus.SUCCESS


class CrawlerRunner:
    def __init__(
        self,
        executor: CrawlerExecutor,
        clock: Callable[[], datetime] = _utc_now,
        run_id_factory: Callable[[], str] = _new_run_id,
        recorder: CrawlRunRecorder | None = None,
    ) -> None:
        self._executor = executor
        self._clock = clock
        self._run_id_factory = run_id_factory
        self._recorder = recorder

    def _record(self, site_id: str, result: CrawlRunResult) -> CrawlRunResult:
        if self._recorder is not None:
            self._recorder.record(site_id=site_id, result=result)
        return result

    def run(self, config: CrawlerConfig) -> CrawlRunResult:
        if not isinstance(config, CrawlerConfig):
            raise TypeError("config must be a CrawlerConfig")

        crawl_run_id = self._run_id_factory()

        if (
            not isinstance(crawl_run_id, str)
            or not crawl_run_id.strip()
        ):
            raise ValueError(
                "run_id_factory must be a non-empty string"
            )

        crawl_run_id = crawl_run_id.strip()
        started_at = _validate_utc_datetime(
            self._clock(),
            "started_at",
        )

        logger.info(
            "Crawl run %s started for site %s",
            crawl_run_id,
            config.site_id,
        )

        try:
            report = self._executor.execute(
                config=config,
                crawl_run_id=crawl_run_id,
            )

            if not isinstance(report, CrawlExecutionReport):
                raise TypeError(
                    "executor must return a CrawlExecutionReport"
                )

        except Exception as exc:
            finished_at = _validate_utc_datetime(
                self._clock(),
                "finished_at",
            )

            logger.exception(
                "Crawl run %s failed for site %s",
                crawl_run_id,
                config.site_id,
            )

            return self._record(config.site_id, CrawlRunResult(
                crawl_run_id=crawl_run_id,
                status=CrawlStatus.FAILED,
                started_at=started_at,
                finished_at=finished_at,
                error=f"{type(exc).__name__}: {exc}",
            ))

        finished_at = _validate_utc_datetime(
            self._clock(),
            "finished_at",
        )

        status = _classify_status(report)

        logger.info(
            "Crawl run %s finished for site %s "
            "with status=%s in %.2fs",
            crawl_run_id,
            config.site_id,
            status,
            (finished_at - started_at).total_seconds(),
        )

        return self._record(config.site_id, CrawlRunResult(
            crawl_run_id=crawl_run_id,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            items_scraped=report.items_scraped,
            request_failures=report.request_failures,
            finish_reason=report.finish_reason,
        ))
