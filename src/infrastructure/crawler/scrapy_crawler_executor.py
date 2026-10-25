from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from collections import deque
from pathlib import Path

from src.application.crawler.crawler_executor import (
    CrawlExecutionReport,
)
from src.domain.entities.crawler_config import CrawlerConfig

_STDERR_TAIL_LINES = 100


class ScrapyCrawlerExecutor:
    def __init__(
        self,
        *,
        timeout_seconds: int = 3800,
        closespider_timeout: int = 3600,
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

        process = subprocess.Popen(
            [sys.executable, str(self._worker_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=project_root,
            env=environment,
        )

        stdout_chunks: list[str] = []
        stderr_tail: deque[str] = deque(maxlen=_STDERR_TAIL_LINES)

       
        def read_stdout() -> None:
            try:
                for line in process.stdout:
                    stdout_chunks.append(line)
            except Exception as e:
                sys.stderr.write(f"[Crawl Error] Đọc stdout thất bại: {e}\n")

        
        def forward_stderr() -> None:
            try:
                for line in process.stderr:
                    stderr_tail.append(line)
                    sys.stderr.write(f"[crawl {crawl_run_id[:8]}] {line}")
                    sys.stderr.flush()
            except Exception as e:
                sys.stderr.write(f"[Crawl Error] Stream stderr thất bại: {e}\n")

        readers = [
            threading.Thread(target=read_stdout, daemon=True),
            threading.Thread(target=forward_stderr, daemon=True),
        ]

        for reader in readers:
            reader.start()


        try:
            process.stdin.write(json.dumps(payload))
            process.stdin.close()
        except BrokenPipeError:
            pass


        try:
            returncode = process.wait(timeout=self._timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            process.wait()
            raise TimeoutError(
                f"Scrapy worker timed out after {self._timeout_seconds}s"
            ) from exc
        finally:
            for reader in readers:
                reader.join(timeout=5)

        stdout = "".join(stdout_chunks).strip()

        if returncode != 0:
            error_log_tail = "".join(stderr_tail)[-4000:]
            raise RuntimeError(
                f"Scrapy worker failed (exit_code={returncode}); "
                f"stderr={error_log_tail!r}"
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
