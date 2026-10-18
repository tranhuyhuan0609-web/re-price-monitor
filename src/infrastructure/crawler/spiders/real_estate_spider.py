from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urldefrag, urlsplit

import scrapy
from scrapy import Request
from scrapy.http import Response, TextResponse

from src.domain.entities.crawler_config import CrawlerConfig
from src.application.parsers.listings_parser import ListingParser
from src.domain.entities.raw_event import (
    RawEventBuilder,
    RawEventBuildError,
)


class RealEstateSpider(scrapy.Spider):
    """
    Crawl listing pages (following "next page" links) and yield RawEvents.

    Must be started programmatically, e.g.
        process.crawl(RealEstateSpider, config=..., crawl_run_id=...,
                      event_builder=...)
    because config and event_builder are objects, not CLI strings.
    """

    name = "real_estate"

    def __init__(
        self,
        *,
        config: CrawlerConfig,
        crawl_run_id: str,
        event_builder: RawEventBuilder,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)

        if not isinstance(config, CrawlerConfig):
            raise TypeError("config must be a CrawlerConfig")

        if not isinstance(crawl_run_id, str) or not crawl_run_id.strip():
            raise ValueError("crawl_run_id must not be blank")

        self.config = config
        self.crawl_run_id = crawl_run_id.strip()
        self.event_builder = event_builder

        self.parser = ListingParser(
            source=config.site_id,
            selectors=config.selectors.to_parser_dict(),
            allowed_domains=config.allowed_domains,
        )

        self.allowed_domains = list(config.allowed_domains)
        # HttpUrl objects are not str; Scrapy needs plain strings.
        self.start_urls = [str(url) for url in config.start_urls]

        # Page budget is per run and shared by all start URLs.
        self._pages_scheduled = len(self.start_urls)
        self._seen_pages: set[str] = set(self.start_urls)
        self._seen_listing_keys: set[str] = set()  # for duplicate_url stats

    # ------------------------------------------------------------------ requests

    def _initial_requests(self) -> Iterator[Request]:
        for url in self.start_urls:
            yield Request(
                url=url,
                callback=self.parse,
                errback=self.handle_request_error,
                dont_filter=True,
                meta={
                    "playwright": True,
                    "playwright_include_page": False,
                },
            )
    async def start(self):
        for request in self._initial_requests():
            yield request

    # ------------------------------------------------------------------ parsing

    def parse(self, response: Response):
        """Convert a listing page into RawEvents and follow the next page."""
        stats = self.crawler.stats
        if response.status >= 400:
            stats.inc_value("request/failed")
            if response.status in {403, 429, 503}:
                stats.inc_value("listing/blocked_response")
            self.logger.warning(
                "HTTP error site=%s status=%s url=%s",
                self.config.site_id,
                response.status,
                response.url,
            )
            if response.status in {403, 429}:
                self.logger.warning(
                    "Stopping site=%s after HTTP %s; "
                    "the site requires a slower or authorized crawl.",
                    self.config.site_id,
                    response.status,
                )
                self.crawler.engine.close_spider(
                    self,
                    reason=f"http_{response.status}",
                )
            return

        if not isinstance(response, TextResponse):
            stats.inc_value("listing/non_text_response")
            self.logger.warning("Skip non-text response: %s", response.url)
            return

        crawled_at = datetime.now(timezone.utc)  # one timestamp per page
        listings, parse_stats = self.parser.parse_with_stats(response)

        stats.inc_value("listing/pages_parsed")
        stats.inc_value("listing/items_found", parse_stats.items_found)
        stats.inc_value("listing/invalid_url", parse_stats.invalid_url)
        stats.inc_value("listing/duplicate_url", parse_stats.duplicate_url)

        self.logger.debug(
            "Parsed %s page=%s found=%d parsed=%d",
            self.config.site_id,
            response.url,
            parse_stats.items_found,
            parse_stats.parsed,
        )

        for listing in listings:
            listing_key = listing.listing_key
            if listing_key in self._seen_listing_keys:
                stats.inc_value("listing/duplicate_listing_key")
                self.logger.debug(
                    "Skip duplicate listing key=%s url=%s",
                    listing.source,
                    listing_key,
                )
                continue
            self._seen_listing_keys.add(listing_key)
            try:
                event = self.event_builder.build(
                    listing,
                    self.crawl_run_id,
                    parser_version=self.config.parser_version,
                    crawled_at=crawled_at,
                )
            except RawEventBuildError as exc:
                stats.inc_value("listing/rejected")
                self.logger.warning("Rejected %s: %s", listing.url, exc)
                continue

            stats.inc_value("listing/events")
            stats.inc_value("listing/raw_events_built")
            yield event

        next_request = self._next_page_request(response, parse_stats.items_found)
        if next_request is not None:
            yield next_request

    def _next_page_request(
        self,
        response: TextResponse,
        items_found: int,
    ) -> Request | None:
        pagination = self.config.pagination
        stats = self.crawler.stats

        if not pagination.enabled or pagination.next_page is None:
            return None

        if items_found == 0:
            # Empty page: likely the end, or a layout change. Do not keep going.
            self.logger.info("No listings on %s; stop paginating", response.url)
            return None

        href = response.css(pagination.next_page).get()
        if not href or not href.strip():
            return None  # last page

        try:
            url = urldefrag(response.urljoin(href.strip()))[0]
            parts = urlsplit(url)
            allowed = (
                parts.scheme in {"http", "https"}
                and bool(parts.hostname)
                and self.config.is_allowed_domain(parts.hostname)
            )
        except ValueError:
            allowed = False

        if not allowed:
            stats.inc_value("pagination/rejected_link")
            self.logger.warning("Rejected next-page link on %s: %r", response.url, href)
            return None

        if url in self._seen_pages:
            stats.inc_value("pagination/already_seen")
            return None

        if self._pages_scheduled >= pagination.max_pages:
            stats.inc_value("pagination/max_pages_reached")
            self.logger.info("max_pages=%d reached; stop paginating", pagination.max_pages)
            return None

        self._seen_pages.add(url)
        self._pages_scheduled += 1
        stats.inc_value("pagination/pages_scheduled")

        return Request(
            url=url,
            callback=self.parse,
            errback=self.handle_request_error,
            meta={
                "playwright": True,
                "playwright_include_page": False,
            },
        )

    # ------------------------------------------------------------------ errors

    def handle_request_error(self, failure) -> None:
        """Runs after Scrapy's retry middleware has given up on the request."""
        request = getattr(failure, "request", None)
        self.crawler.stats.inc_value("request/failed")
        self.logger.error(
            "Request failed site=%s url=%s: %s",
            self.config.site_id,
            request.url if request is not None else "?",
            failure.getErrorMessage(),
        )