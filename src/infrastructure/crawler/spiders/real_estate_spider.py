from __future__ import annotations
from src.infrastructure.crawler.detail_extractors.factory import create_detail_extractor
from collections.abc import AsyncIterator, Iterator
from dataclasses import replace
import json
from html import unescape
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urldefrag, urlsplit

import scrapy
from scrapy import Request
from scrapy.http import Response, TextResponse
from scrapy.selector import Selector
from scrapy.utils.defer import maybe_deferred_to_future
from twisted.internet.threads import deferToThread

from src.infrastructure.database.postgres_listing_detail_cache import (
    PostgresListingDetailCache,
)

from src.application.parsers.listings_parser import ListingParser, ParsedListing
from src.domain.entities.crawler_config import CrawlerConfig
from src.domain.entities.raw_event import (
    RawEvent,
    RawEventBuilder,
    RawEventBuildError,
)


class RealEstateSpider(scrapy.Spider):
    """Crawl listing pages, then detail pages when configured fields are missing.

    Flow:
        listing page -> parse cards -> optional detail request -> RawEvent

    Requests do not opt into Playwright. The Scrapy handler configured by the
    worker can therefore use the regular HTTP download path for these requests.
    """

    name = "real_estate"

    def __init__(
        self,
        *,
        config: CrawlerConfig,
        crawl_run_id: str,
        event_builder: RawEventBuilder,
        detail_cache: PostgresListingDetailCache | None = None,
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
        self.selectors = config.selectors.to_parser_dict()
        self.detail_extractor = create_detail_extractor(
            config.detail_extractor,
            selectors=self.selectors,
)
        self.detail_cache = detail_cache
        self._detail_cache_usable = detail_cache is not None
        self._detail_cache_writes_usable = detail_cache is not None
        self._detail_cache_lookup_failure_logged = False
        self._detail_cache_write_failure_logged = False

        self.parser = ListingParser(
            source=config.site_id,
            selectors=self.selectors,
            allowed_domains=config.allowed_domains,
        )

        self.allowed_domains = list(config.allowed_domains)
        # HttpUrl objects are not str; Scrapy needs plain strings.
        self.start_urls = [str(url) for url in config.start_urls]

        # max_pages is the total budget for listing pages in this run.
        self._max_pages = max(1, int(config.pagination.max_pages))
        if len(self.start_urls) > self._max_pages:
            self.logger.warning(
                "start_urls=%d exceeds max_pages=%d; only scheduling the first %d start URLs",
                len(self.start_urls),
                self._max_pages,
                self._max_pages,
            )
            self.start_urls = self.start_urls[: self._max_pages]

        self._pages_scheduled = len(self.start_urls)
        self._seen_pages: set[str] = set(self.start_urls)
        self._seen_listing_keys: set[str] = set()

    # ------------------------------------------------------------------ requests

    def _initial_requests(self) -> Iterator[Request]:
        for url in self.start_urls:
            yield Request(
                url=url,
                callback=self.parse,
                errback=self.handle_request_error,
                dont_filter=True,
                meta={"handle_httpstatus_all": True},
            )

    async def start(self) -> AsyncIterator[Request]:
        for request in self._initial_requests():
            yield request

    # ------------------------------------------------------------------ listing page

    async def parse(self, response: Response) -> AsyncIterator[Request | RawEvent]:
        """Parse listing cards, reuse cached details, and paginate asynchronously."""
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
                    "Stopping site=%s after HTTP %s; reduce crawl rate or verify permitted access.",
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
            self.logger.warning("Skip non-text listing response: %s", response.url)
            return

        crawled_at = datetime.now(timezone.utc)
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

        # Reserve keys before awaiting the cache query so concurrent page
        # callbacks cannot schedule the same listing twice in one run.
        unique_listings: list[ParsedListing] = []
        for listing in listings:
            listing_key = listing.listing_key
            if listing_key in self._seen_listing_keys:
                stats.inc_value("listing/duplicate_listing_key")
                continue
            self._seen_listing_keys.add(listing_key)
            unique_listings.append(listing)

        cache_rows: dict[str, dict[str, Any]] = {}
        if self._detail_cache_usable and self._required_detail_fields():
            try:
                cache_rows = await maybe_deferred_to_future(
                    deferToThread(
                        self.detail_cache.get_many,
                        self.config.site_id,
                        [listing.listing_key for listing in unique_listings],
                    )
                )
                stats.inc_value("detail/cache_lookup_batches")
                stats.inc_value("detail/cache_rows_loaded", len(cache_rows))
            except Exception as exc:
                stats.inc_value("detail/cache_lookup_failed")
                self._disable_detail_cache(
                    f"Cache lookup failed ({exc!r}); this run will fetch details without caching."
                )
                cache_rows = {}

        for listing in unique_listings:
            cached = cache_rows.get(listing.listing_key)
            effective_listing = self._merge_cached_detail(listing, cached)

            if not self._should_fetch_detail(listing, cached):
                if cached is not None:
                    stats.inc_value("detail/cache_hit")
                stats.inc_value("detail/request_skipped")
                event = self._build_raw_event(effective_listing, crawled_at)
                if event is not None:
                    yield event
                continue

            stats.inc_value("detail/request_scheduled")
            yield Request(
                url=listing.url,
                callback=self.parse_detail,
                errback=self.handle_detail_request_error,
                cb_kwargs={
                    "listing": effective_listing,
                    "crawled_at": crawled_at,
                },
                meta={"handle_httpstatus_all": True},
            )

        # Listing pagination is independent from detail-page callbacks.
        next_request = self._next_page_request(response, parse_stats.items_found)
        if next_request is not None:
            yield next_request

    def _required_detail_fields(self) -> tuple[str, ...]:
        return self.detail_extractor.required_fields

    @staticmethod
    def _merge_cached_detail(
        listing: ParsedListing,
        cached: dict[str, Any] | None,
    ) -> ParsedListing:
        """Re-attach known detail fields so list-only events do not erase them."""
        if not cached:
            return listing
        return replace(
            listing,
            description=listing.description or cached.get("description"),
            contact_info=listing.contact_info or cached.get("contact_info"),
        )

    def _should_fetch_detail(
        self,
        listing: ParsedListing,
        cached: dict[str, Any] | None,
    ) -> bool:
        """Fetch details for new/missing data; refresh complete cache periodically."""
        required = self._required_detail_fields()
        if not required:
            return False

        # If the list card itself already supplies every required field, no
        # detail request is needed.
        if all(getattr(listing, name, None) for name in required):
            return False

        now = datetime.now(timezone.utc)
        if cached is None:
            return True

        cached_complete = all(cached.get(name) for name in required)
        last_attempt = cached.get("last_attempt_at")
        last_success = cached.get("last_success_at")
        last_outcome = cached.get("last_outcome")

        if cached_complete:
            if isinstance(last_success, datetime):
                age = (now - last_success).total_seconds()
                if age < self.detail_cache.refresh_after_seconds:
                    return False
            # Avoid immediately repeating a failed refresh of otherwise usable
            # cached data. It can be retried after the missing/retry cooldown.
            if (
                last_outcome == "failed"
                and isinstance(last_attempt, datetime)
                and (now - last_attempt).total_seconds()
                < self.detail_cache.retry_missing_after_seconds
            ):
                return False
            return True

        # A previous request may have had no public phone/description. Do not
        # re-fetch on every 5-minute schedule; retry after the configured cooloff.
        if not isinstance(last_attempt, datetime):
            return True
        return (now - last_attempt).total_seconds() >= (
            self.detail_cache.retry_missing_after_seconds
        )

    async def _persist_detail_cache(
        self,
        listing: ParsedListing,
        *,
        description: str | None,
        contact_info: str | None,
        fetch_succeeded: bool,
    ) -> None:
        if (
            not self._detail_cache_usable
            or not self._detail_cache_writes_usable
            or self.detail_cache is None
        ):
            return
        try:
            await maybe_deferred_to_future(
                deferToThread(
                    self.detail_cache.upsert,
                    site_id=self.config.site_id,
                    listing_key=listing.listing_key,
                    listing_url=listing.url,
                    description=description,
                    contact_info=contact_info,
                    fetch_succeeded=fetch_succeeded,
                )
            )
            self.crawler.stats.inc_value("detail/cache_writes")
        except Exception as exc:
            self.crawler.stats.inc_value("detail/cache_write_failed")
            self._detail_cache_writes_usable = False
            if not self._detail_cache_write_failure_logged:
                self.logger.warning(
                    "Cache writes disabled after failure (%r); existing cache reads remain enabled.",
                    exc,
                )
                self._detail_cache_write_failure_logged = True

    def _disable_detail_cache(self, message: str) -> None:
        self._detail_cache_usable = False
        self._detail_cache_writes_usable = False
        if not self._detail_cache_lookup_failure_logged:
            self.logger.warning(message)
            self._detail_cache_lookup_failure_logged = True

    # ------------------------------------------------------------------ detail page

    async def parse_detail(
        self,
        response: Response,
        listing: ParsedListing,
        crawled_at: datetime,
    ) -> list[RawEvent]:
        """Extract detail fields, update persistent cache, and emit one RawEvent."""
        stats = self.crawler.stats

        if response.status >= 400 or not isinstance(response, TextResponse):
            stats.inc_value("detail/failed")
            self.logger.warning(
                "Cannot parse detail page: status=%s url=%s",
                response.status,
                response.url,
            )

            if response.status in {403, 429}:
                stats.inc_value("detail/blocked_response")
                self.crawler.engine.close_spider(
                    self,
                    reason=f"detail_http_{response.status}",
                )

            await self._persist_detail_cache(
                listing,
                description=None,
                contact_info=None,
                fetch_succeeded=False,
            )
            event = self._build_raw_event(listing, crawled_at)
            return [event] if event is not None else []

        description = self.detail_extractor.extract_description(response)
        if description:
            stats.inc_value("detail/description_found")
        else:
            stats.inc_value("detail/description_missing")
            self.logger.debug(
                "Description not found site=%s url=%s selector=%r response_chars=%d",
                self.config.site_id,
                response.url,
                self.selectors.get("description"),
                len(response.text),
            )

        contact_info = self.detail_extractor.extract_contact_info(response)
        stats.inc_value("detail/pages_parsed")
        stats.inc_value("detail/contact_found", int(bool(contact_info)))

        # Persist before publishing. If Kafka later fails, a future list crawl
        # can re-attach the cached fields and publish them again. The SQL upsert
        # preserves previously known values if a field is absent this time.
        await self._persist_detail_cache(
            listing,
            description=description,
            contact_info=contact_info,
            fetch_succeeded=True,
        )

        enriched_listing = replace(
            listing,
            description=description or listing.description,
            contact_info=contact_info or listing.contact_info,
        )

        self.logger.debug(
            "Parsed detail site=%s url=%s description_found=%s contact_found=%s",
            self.config.site_id,
            response.url,
            bool(description),
            bool(contact_info),
        )

        event = self._build_raw_event(enriched_listing, crawled_at)
        return [event] if event is not None else []



    
    # ------------------------------------------------------------------ event builder

    def _build_raw_event(
        self,
        listing: ParsedListing,
        crawled_at: datetime,
    ) -> RawEvent | None:
        """Build a validated RawEvent from a parsed listing."""
        stats = self.crawler.stats

        try:
            event = self.event_builder.build(
                listing,
                self.crawl_run_id,
                parser_version=self.config.parser_version,
                crawled_at=crawled_at,
            )
        except RawEventBuildError as exc:
            stats.inc_value("listing/rejected")
            self.logger.warning(
                "Rejected listing url=%s error=%s",
                listing.url,
                exc,
            )
            return None

        stats.inc_value("listing/events")
        stats.inc_value("listing/raw_events_built")
        return event

    # ------------------------------------------------------------------ pagination

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
            self.logger.info("No listings on %s; stop paginating", response.url)
            return None

        href = response.css(pagination.next_page).get()
        if not href or not href.strip():
            return None

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
            self.logger.warning(
                "Rejected next-page link on %s: %r",
                response.url,
                href,
            )
            return None

        if url in self._seen_pages:
            stats.inc_value("pagination/already_seen")
            return None

        if self._pages_scheduled >= self._max_pages:
            stats.inc_value("pagination/max_pages_reached")
            self.logger.info(
                "max_pages=%d reached; stop paginating",
                self._max_pages,
            )
            return None

        self._seen_pages.add(url)
        self._pages_scheduled += 1
        stats.inc_value("pagination/pages_scheduled")

        return Request(
            url=url,
            callback=self.parse,
            errback=self.handle_request_error,
            meta={"handle_httpstatus_all": True},
        )

    # ------------------------------------------------------------------ errors

    async def handle_detail_request_error(self, failure) -> list[RawEvent]:
        """Emit listing-page data and record failed detail attempts after retries."""
        request = getattr(failure, "request", None)
        self.crawler.stats.inc_value("detail/request_failed")

        self.logger.error(
            "Detail request failed site=%s url=%s: %s",
            self.config.site_id,
            request.url if request is not None else "?",
            failure.getErrorMessage(),
        )

        if request is None:
            return []

        listing = request.cb_kwargs.get("listing")
        crawled_at = request.cb_kwargs.get("crawled_at")
        if listing is None or crawled_at is None:
            return []

        await self._persist_detail_cache(
            listing,
            description=None,
            contact_info=None,
            fetch_succeeded=False,
        )
        event = self._build_raw_event(listing, crawled_at)
        return [event] if event is not None else []

    def handle_request_error(self, failure) -> None:
        """Handle failed listing-page requests after Scrapy retries."""
        request = getattr(failure, "request", None)
        self.crawler.stats.inc_value("request/failed")
        self.logger.error(
            "Request failed site=%s url=%s: %s",
            self.config.site_id,
            request.url if request is not None else "?",
            failure.getErrorMessage(),
        )
