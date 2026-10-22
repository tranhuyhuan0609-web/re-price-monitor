from __future__ import annotations
import json
import logging
import os
import random as random_hh
import sys
import traceback
from pathlib import Path
from typing import Any, TextIO
from dotenv import load_dotenv
from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings
from twisted.python.failure import Failure
from src.domain.entities.crawler_config import CrawlerConfig
from src.domain.entities.raw_event import RawEventBuilder
from src.infrastructure.crawler.spiders.real_estate_spider import RealEstateSpider
from src.infrastructure.database.postgres_listing_detail_cache import (
    PostgresListingDetailCache,
)

logger = logging.getLogger(__name__)

ITEM_PIPELINES: dict[str, int] = {
    "src.infrastructure.crawler.pipelines.raw_event_kafka_pipeline."
    "RawEventKafkaPipeline": 300,
}

DEFAULT_BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0"
)
DEFAULT_CLOSESPIDER_TIMEOUT = 7200


def _load_runtime_environment() -> None:
    """Load the selected environment for a standalone worker process."""
    project_root = Path(__file__).resolve().parents[3]
    load_dotenv(project_root / ".env")
    environment = os.environ.get("ENV", "dev").strip()
    load_dotenv(project_root / f".env.{environment}")


def _write_result(result: dict[str, Any], stream: TextIO) -> None:
    """Write exactly one JSON line for the executor to parse."""
    stream.write(
        json.dumps(result, ensure_ascii=True, separators=(",", ":")) + "\n"
    )
    stream.flush()


def _read_payload() -> dict[str, Any]:
    """Read one JSON object from stdin."""
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
    # bool is a subclass of int in Python, so reject it explicitly.
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{key} must be a positive integer.")
    return value


def _optional_bool(
    payload: dict[str, Any],
    key: str,
    default: bool,
) -> bool:
    value = payload.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value


def _build_scrapy_settings(
    config: CrawlerConfig,
    *,
    closespider_timeout: int,
    publish_kafka: bool = True,
    browser_headless: bool = True,
) -> dict[str, Any]:
    """Map domain crawler configuration to Scrapy runtime settings.

    Concurrency is bounded per domain to avoid flooding a source website,
    while allowing more than one request at a time. AutoThrottle adapts to
    response latency and errors.
    """
    if config.proxy_settings.enabled:
        raise NotImplementedError("Proxy support is not implemented yet.")

    if publish_kafka and not ITEM_PIPELINES:
        raise NotImplementedError(
            "No item pipeline configured; refusing to discard scraped items."
        )

    crawler_settings = config.crawler_settings

    # Use a moderate performance profile and keep hard safety caps. The DB
    # setting still controls concurrency, but a typo cannot create an
    # unbounded burst toward a source website.
    requested_concurrency = max(1, int(crawler_settings.concurrent_requests))
    global_concurrency = min(requested_concurrency, 8)
    per_domain_concurrency = min(global_concurrency, 5)
    target_concurrency = min(float(per_domain_concurrency), 4.0)
    base_delay = crawler_settings.delay
    delay = random_hh.uniform(float(base_delay)-1.0, float(base_delay)+1.0)
    selector_agent = random_hh.choice(DEFAULT_BROWSER_USER_AGENT)
    settings: dict[str, Any] = {
        "ROBOTSTXT_OBEY": False,
        "USER_AGENT": selector_agent,

        # Throughput: global max 8; at most 5 requests per domain.
        # The database value must be raised (e.g. to 5) for this to take effect.
        "DOWNLOAD_DELAY": delay,
        "RANDOMIZE_DOWNLOAD_DELAY": crawler_settings.randomize_delay,
        "CONCURRENT_REQUESTS": global_concurrency,
        "CONCURRENT_REQUESTS_PER_DOMAIN": per_domain_concurrency,

        # Adaptive throttling targets up to 4 in-flight requests, while
        # preserving the configured delay as the minimum request delay.
        "RETRY_ENABLED": crawler_settings.retry_enabled,
        "RETRY_TIMES": crawler_settings.max_retries,
        # Do not retry 429: allow Spider to stop promptly on rate limiting.
        # Continue retrying transient network/server failures such as 503.
        "RETRY_HTTP_CODES": [408, 425, 500, 502, 503, 504],
        "DOWNLOAD_TIMEOUT": crawler_settings.download_timeout,
        "HTTPERROR_ALLOW_ALL": True,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": target_concurrency,
        "AUTOTHROTTLE_START_DELAY": delay,
        "AUTOTHROTTLE_MAX_DELAY": max(delay * 4, 8.0),
        "AUTOTHROTTLE_DEBUG": False,

        "COOKIES_ENABLED": True,
        "CLOSESPIDER_TIMEOUT": closespider_timeout,
        "ITEM_PIPELINES": ITEM_PIPELINES if publish_kafka else {},
        # "DOWNLOAD_HANDLERS": {
        #     "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        #     "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        # },
        "TWISTED_REACTOR": (
            "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
        ),
        # "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        # "PLAYWRIGHT_LAUNCH_OPTIONS": {
        #     "headless": browser_headless,
        #     "args": ["--disable-blink-features=AutomationControlled"]
        # },
        # "PLAYWRIGHT_CONTEXTS": {
        #     "default": {
        #         "user_agent": selector_agent,
        #         "locale": "vi-VN",
        #         "timezone_id": "Asia/Ho_Chi_Minh",
        #         "extra_http_headers": {
        #             "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        #         },
        #     },
        # },
        "TELNETCONSOLE_ENABLED": False,
        "LOG_LEVEL": "INFO",
    }

    bootstrap_servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS")
    raw_topic = os.environ.get("KAFKA_RAW_TOPIC")
    if bootstrap_servers:
        settings["KAFKA_BOOTSTRAP_SERVERS"] = bootstrap_servers
    if raw_topic:
        settings["KAFKA_RAW_TOPIC"] = raw_topic

    return settings


def _build_report(
    stats: dict[str, Any],
    crawl_run_id: str,
) -> dict[str, Any]:
    """Return crawl statistics for the application layer."""
    return {
        "status": "ok",
        "crawl_run_id": crawl_run_id,
        "items_scraped": int(stats.get("item_scraped_count", 0)),
        "raw_events_built": int(stats.get("listing/raw_events_built", 0)),
        "requests_total": int(stats.get("downloader/request_count", 0)),
        "request_failures": int(
            stats.get("request/failed", 0)
            + stats.get("httperror/response_ignored_count", 0)
            + stats.get("listing/blocked_response", 0)
        ),
        "http_responses_ignored": int(
            stats.get("httperror/response_ignored_count", 0)
        ),
        "finish_reason": stats.get("finish_reason"),
        "elapsed_time_seconds": round(
            (stats["finish_time"] - stats["start_time"]).total_seconds(), 3
        )
        if stats.get("finish_time") and stats.get("start_time")
        else None,
        "listing_pages_parsed": int(stats.get("listing/pages_parsed", 0)),
        "listings_found": int(stats.get("listing/items_found", 0)),
        "detail_pages_parsed": int(stats.get("detail/pages_parsed", 0)),
        "detail_request_failed": int(stats.get("detail/request_failed", 0)),
        "description_found": int(stats.get("detail/description_found", 0)),
        "description_missing": int(stats.get("detail/description_missing", 0)),
        "contact_found": int(stats.get("detail/contact_found", 0)),
        "detail_requests_scheduled": int(stats.get("detail/request_scheduled", 0)),
        "detail_requests_skipped": int(stats.get("detail/request_skipped", 0)),
        "detail_cache_hits": int(stats.get("detail/cache_hit", 0)),
        "detail_cache_rows_loaded": int(stats.get("detail/cache_rows_loaded", 0)),
        "detail_cache_writes": int(stats.get("detail/cache_writes", 0)),
        "detail_cache_lookup_failed": int(stats.get("detail/cache_lookup_failed", 0)),
        "detail_cache_write_failed": int(stats.get("detail/cache_write_failed", 0)),
        "items_per_second": round(
            int(stats.get("listing/raw_events_built", 0))
            / max((stats["finish_time"] - stats["start_time"]).total_seconds(), 0.001),
            3,
        )
        if stats.get("finish_time") and stats.get("start_time")
        else None,
    }


def run_worker(payload: dict[str, Any]) -> dict[str, Any]:
    """Run one crawl in a separate worker process."""
    _load_runtime_environment()
    crawl_run_id = _require_text(payload, "crawl_run_id")
    config_json = _require_text(payload, "config_json")

    closespider_timeout = _optional_positive_int(
        payload,
        "closespider_timeout",
        DEFAULT_CLOSESPIDER_TIMEOUT,
    )
    publish_kafka = _optional_bool(payload, "publish_kafka", True)
    browser_headless = _optional_bool(payload, "browser_headless", True)

    try:
        config_data = json.loads(config_json)
    except json.JSONDecodeError as exc:
        raise ValueError("Worker payload must be valid JSON.") from exc

    config = CrawlerConfig.model_validate(config_data)
    if not config.enabled:
        raise ValueError(f"Crawler site {config.site_id!r} is disabled.")

    scrapy_settings = Settings()
    scrapy_settings.setdict(
        _build_scrapy_settings(
            config,
            closespider_timeout=closespider_timeout,
            publish_kafka=publish_kafka,
            browser_headless=browser_headless,
        ),
        priority="project",
    )

    # The persistent cache prevents detail pages from being downloaded on
    # every scheduled run. A migration must be applied before using this mode.
    selector_dict = config.selectors.to_parser_dict()
    needs_detail_cache = bool(
        selector_dict.get("description")
        or selector_dict.get("contact_info")
        or config.site_id.strip().lower() == "meeyland"
    )
    detail_cache: PostgresListingDetailCache | None = None
    if needs_detail_cache:
        detail_cache = PostgresListingDetailCache.from_environment()
        try:
            detail_cache.check_schema()
        except Exception as exc:
            detail_cache.close()
            raise RuntimeError(
                "The table crawler_listing_detail_cache is missing or unavailable. "
                "Apply sql/001_create_listing_detail_cache.sql before running "
                "the selective detail-crawl mode."
            ) from exc

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
        detail_cache=detail_cache,
    ).addErrback(capture_failure)

    # This worker performs one crawl, so the reactor starts exactly once.
    try:
        process.start()
    finally:
        if detail_cache is not None:
            detail_cache.close()

    if failures:
        failure = failures[0]
        raise RuntimeError(
            f"Spider execution failed: {failure.getErrorMessage()}"
        ) from failure.value

    return _build_report(crawler.stats.get_stats(), crawl_run_id)


def main() -> int:
    # stdout is reserved for the JSON protocol; other logs go to stderr.
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
