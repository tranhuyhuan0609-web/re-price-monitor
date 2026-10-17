
from __future__ import annotations

import json
import logging
import sys
import traceback
from typing import Any, TextIO

from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings
from twisted.python.failure import Failure

from src.domain.entities.crawler_config import CrawlerConfig
from src.domain.entities.raw_event import RawEventBuilder
from src.infrastructure.crawler.spiders.real_estate_spider import RealEstateSpider

logger = logging.getLogger(__name__)

# Đăng ký pipeline thật khi bước tích hợp pipeline được triển khai.
ITEM_PIPELINES: dict[str, int] = {}

DEFAULT_USER_AGENT = "RealEstateCrawler/1.0"
DEFAULT_CLOSESPIDER_TIMEOUT = 1800


def _write_result(result: dict[str, Any], stream: TextIO) -> None:
    """Ghi đúng một dòng JSON để executor parse."""
    stream.write(
        json.dumps(result, ensure_ascii=True, separators=(",", ":")) + "\n"
    )
    stream.flush()


def _read_payload() -> dict[str, Any]:
    """Đọc một JSON object từ stdin."""
    line = sys.stdin.readline()

    if not line.strip():
        raise ValueError("Missing worker payload on stdin.")

    try:
        payload = json.loads(line)
    except json.JSONDecodeError as exc:
        raise ValueError("Worker payload must be valid JSON.") from exc

    if not isinstance(payload, dict):
        raise ValueError("Worker payload must be a JSON object.")

    return payload


def _require_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string.")

    return value.strip()


def _optional_positive_int(
    payload: dict[str, Any],
    key: str,
    default: int,
) -> int:
    value = payload.get(key, default)

    # bool là subclass của int trong Python nên phải loại riêng.
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{key} must be a positive integer.")

    return value


def _build_scrapy_settings(
    config: CrawlerConfig,
    *,
    closespider_timeout: int,
) -> dict[str, Any]:
    """Chuyển cấu hình domain thành Scrapy settings."""
    if config.proxy_settings.enabled:
        raise NotImplementedError("Proxy support is not implemented yet.")

    if not ITEM_PIPELINES:
        raise NotImplementedError(
            "No item pipeline configured; refusing to discard scraped items."
        )

    crawler_settings = config.crawler_settings

    return {
        "ROBOTSTXT_OBEY": True,
        "USER_AGENT": DEFAULT_USER_AGENT,
        "DOWNLOAD_DELAY": crawler_settings.delay,
        "RANDOMIZE_DOWNLOAD_DELAY": crawler_settings.randomize_delay,
        "CONCURRENT_REQUESTS": crawler_settings.concurrent_requests,
        "DOWNLOAD_TIMEOUT": crawler_settings.download_timeout,
        "RETRY_ENABLED": crawler_settings.retry_enabled,
        "RETRY_TIMES": crawler_settings.max_retries,
        "AUTOTHROTTLE_ENABLED": True,
        "CLOSESPIDER_TIMEOUT": closespider_timeout,
        "ITEM_PIPELINES": ITEM_PIPELINES,
        "TELNETCONSOLE_ENABLED": False,
        "LOG_LEVEL": "INFO",
    }


def _build_report(
    stats: dict[str, Any],
    crawl_run_id: str,
) -> dict[str, Any]:
    """Trả số liệu thô; Application chịu trách nhiệm phân loại trạng thái."""
    return {
        "status": "ok",
        "crawl_run_id": crawl_run_id,
        "items_scraped": int(stats.get("item_scraped_count", 0)),
        "requests_total": int(stats.get("downloader/request_count", 0)),
        "request_failures": int(stats.get("request/failed", 0)),
        "http_responses_ignored": int(
            stats.get("httperror/response_ignored_count", 0)
        ),
        "finish_reason": stats.get("finish_reason"),
    }


def run_worker(payload: dict[str, Any]) -> dict[str, Any]:
    """Chạy một crawl trong một process riêng."""
    crawl_run_id = _require_text(payload, "crawl_run_id")
    config_json = _require_text(payload, "config_json")

    closespider_timeout = _optional_positive_int(
        payload,
        "closespider_timeout",
        DEFAULT_CLOSESPIDER_TIMEOUT,
    )
    try:
        config_data = json.loads(config_json)
    except json.JSONDecodeError as exc:
        raise ValueError(
        "Worker payload must be valid JSON."
    ) from exc

    config = CrawlerConfig.model_validate(config_data)

    if not config.enabled:
        raise ValueError(f"Crawler site {config.site_id!r} is disabled.")

    scrapy_settings = Settings()
    scrapy_settings.setdict(
        _build_scrapy_settings(
            config,
            closespider_timeout=closespider_timeout,
        ),
        priority="project",
    )

    process = CrawlerProcess(settings=scrapy_settings)
    crawler = process.create_crawler(RealEstateSpider)

    failures: list[Failure] = []

    def capture_failure(failure: Failure) -> None:
        failures.append(failure)

    process.crawl(
        crawler,
        config=config,
        crawl_run_id=crawl_run_id,
        event_builder=RawEventBuilder(),
    ).addErrback(capture_failure)

    # Worker này chỉ thực hiện một crawl, vì vậy reactor chỉ khởi động một lần.
    process.start()

    if failures:
        failure = failures[0]
        raise RuntimeError(
            f"Spider execution failed: {failure.getErrorMessage()}"
        ) from failure.value

    return _build_report(crawler.stats.get_stats(), crawl_run_id)


def main() -> int:
    # stdout dành riêng cho giao thức JSON; log và print khác đi sang stderr.
    result_stream = sys.stdout
    sys.stdout = sys.stderr

    try:
        result = run_worker(_read_payload())
        _write_result(result, result_stream)
        return 0

    except Exception as exc:
        logger.exception("Scrapy worker failed")

        _write_result(
            {
                "status": "error",
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "traceback": traceback.format_exc(),
            },
            result_stream,
        )
        return 1

    finally:
        sys.stdout = result_stream


if __name__ == "__main__":
    raise SystemExit(main())
