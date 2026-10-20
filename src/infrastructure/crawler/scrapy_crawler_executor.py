from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path
from src.application.crawler.crawler_executor import (
    CrawlExecutionReport,
)
from src.domain.entities.crawler_config import CrawlerConfig


class ScrapyCrawlerExecutor:
    def __init__(
        self,
        *,
        timeout_seconds: int = 1900,
        closespider_timeout: int = 1800,
        worker_path: Path | None = None,
    ) -> None:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, int)
            or timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be a positive integer")

        if (
            isinstance(closespider_timeout, bool)
            or not isinstance(closespider_timeout, int)
            or closespider_timeout <= 0
        ):
            raise ValueError(
                "closespider_timeout must be a positive integer"
            )

        self._timeout_seconds = timeout_seconds
        self._closespider_timeout = closespider_timeout
        self._worker_path = worker_path or Path(__file__).with_name(
            "scrapy_worker.py"
        )

    def execute(
        self,
        config: CrawlerConfig,
        crawl_run_id: str,
    ) -> CrawlExecutionReport:
        if not isinstance(config, CrawlerConfig):
            raise TypeError("config must be a CrawlerConfig")

        if not isinstance(crawl_run_id, str) or not crawl_run_id.strip():
            raise ValueError("crawl_run_id must not be blank")

        if not self._worker_path.is_file():
            raise FileNotFoundError(
                f"Scrapy worker not found: {self._worker_path}"
            )

        crawl_run_id = crawl_run_id.strip()

        payload = {
            "crawl_run_id": crawl_run_id,
            "config_json": config.model_dump_json(),
            "closespider_timeout": self._closespider_timeout,
        }
        project_root = self._worker_path.parents[3]
        environment = os.environ.copy()
        existing_pythonpath = environment.get("PYTHONPATH")
        environment["PYTHONPATH"] = os.pathsep.join(
            path
            for path in (str(project_root), existing_pythonpath)
            if path
        )

        try:
            completed = subprocess.run(
                [sys.executable, str(self._worker_path)],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self._timeout_seconds,
                cwd=project_root,
                env=environment,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                f"Scrapy worker timed out after {self._timeout_seconds}s"
            ) from exc

        stdout = completed.stdout.strip()

        if completed.returncode != 0:
            raise RuntimeError(
                "Scrapy worker failed "
                f"(exit_code={completed.returncode}); "
                f"stderr={completed.stderr[-4000:]!r}"
            )

        if not stdout:
            raise RuntimeError("Scrapy worker returned empty stdout")

        try:
            result = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Scrapy worker returned invalid JSON"
            ) from exc

        if not isinstance(result, dict):
            raise RuntimeError("Worker result must be a JSON object")

        if result.get("status") != "ok":
            raise RuntimeError(
                "Worker error: "
                f"{result.get('error_type')}: "
                f"{result.get('error_message')}"
            )

        if result.get("crawl_run_id") != crawl_run_id:
            raise RuntimeError("Worker crawl_run_id mismatch")

        items_scraped = result.get("items_scraped")
        request_failures = result.get("request_failures")
        finish_reason = result.get("finish_reason")

        if (
            isinstance(items_scraped, bool)
            or not isinstance(items_scraped, int)
            or items_scraped < 0
        ):
            raise RuntimeError("Invalid items_scraped in worker result")

        if (
            isinstance(request_failures, bool)
            or not isinstance(request_failures, int)
            or request_failures < 0
        ):
            raise RuntimeError("Invalid request_failures in worker result")

        if finish_reason is not None and not isinstance(finish_reason, str):
            raise RuntimeError("Invalid finish_reason in worker result")

        return CrawlExecutionReport(
            items_scraped=items_scraped,
            finish_reason=finish_reason,
            request_failures=request_failures,
        )
