from __future__ import annotations
import logging
import re
from src.application.parsers.create_url_hash import create_url_hash
from dataclasses import dataclass
from typing import ClassVar
from src.application.exceptions.listing_parse_exception import ListingParseError
from urllib.parse import urljoin, urlsplit
from scrapy.http import TextResponse
from scrapy.selector import Selector
logger = logging.getLogger(__name__)
_HOST_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
_HOST_RE = re.compile(rf"^{_HOST_LABEL}(?:\.{_HOST_LABEL})*$")
_VALUE_SELECTOR_RE = re.compile(r"::(?:text|attr\([^)]+\))\s*$")
_ATTR_SELECTOR_RE = re.compile(r"::attr\([^)]+\)\s*$")
_ITEM_ATTR_SELECTOR_RE = re.compile(r"^::attr\(([^)]+)\)\s*$")
@dataclass(frozen=True, slots=True)
class ParsedListing:
    source: str
    url: str
    url_hash: str 
    source_listing_id: str | None = None
    title: str | None = None
    description: str | None = None
    raw_price: str | None = None
    raw_address: str | None = None
    raw_area: str | None = None
    contact_info: str | None = None
    raw_payload: str | None = None
    page_url: str | None = None
    quality_flags: tuple[str, ...] = ()
    @property
    def listing_key(self) -> str:
        if self.source_listing_id:
            return f"{self.source}:{self.source_listing_id}"

        return f"{self.source}:url:{self.url_hash}"

@dataclass(frozen=True, slots=True)
class ParserStats:
    items_found: int
    parsed: int
    invalid_url: int
    duplicate_url: int


class ListingParser:
    OPTIONAL_FIELDS: ClassVar[tuple[str, ...]] = (
        "source_listing_id",
        "title",
        "description",
        "raw_price",
        "raw_address",
        "raw_area",
        "contact_info",
    )
    FLAG_FIELDS: ClassVar[tuple[str, ...]] = (
        "source_listing_id",
        "title",
        "raw_price",
        "raw_area",
        "raw_address",
    )
    REQUIRED_SELECTORS: ClassVar[frozenset[str]] = frozenset({"item", "url"})
    ALLOWED_SELECTOR_KEYS: ClassVar[frozenset[str]] = (
        REQUIRED_SELECTORS | frozenset(OPTIONAL_FIELDS)
    )

    def __init__(
        self,
        source: str,
        selectors: dict[str, str],
        allowed_domains: list[str],
        max_payload_chars: int | None = None,
    ) -> None:
        if not isinstance(source, str) or not source.strip():
            raise ValueError("source must be a non-empty string")
        if not isinstance(selectors, dict):
            raise TypeError("selectors must be a dict[str, str]")
        if not isinstance(max_payload_chars, (int, type(None))):
            raise TypeError("max_payload_chars must be an int or None")
        if isinstance(max_payload_chars, (int, type(None))) and not isinstance(max_payload_chars, bool):
            if max_payload_chars is not None and max_payload_chars <= 0:
               raise ValueError("max_payload_chars must be positive or None")
            pass
        else:
            raise TypeError("max_payload_chars must be an int or None")
        missing = self.REQUIRED_SELECTORS - selectors.keys()
        if missing:
            raise ValueError(f"Missing required selectors: {sorted(missing)}")

        unknown = selectors.keys() - self.ALLOWED_SELECTOR_KEYS
        if unknown:
            raise ValueError(
                f"Unknown selector keys: {sorted(unknown)}; "
                f"allowed: {sorted(self.ALLOWED_SELECTOR_KEYS)}"
            )

        cleaned = {}
        for name, selector in selectors.items():
            if not isinstance(selector, str) or not selector.strip():
                raise ValueError(f"Selector '{name}' must be a non-empty string")
            cleaned[name] = selector.strip()
        self._validate_selector_shapes(cleaned)

        self.source = source.strip().lower()
        self.selectors = cleaned
        self.max_payload_chars = max_payload_chars
        self.allowed_domains = self._normalize_domains(allowed_domains)
        # Precomputed for fast suffix matching in _is_allowed_host.
        self._domain_suffixes = tuple("." + d for d in self.allowed_domains)

        # Field extraction plan, computed once instead of per listing.
        self._item_selector = cleaned["item"]
        self._url_selector = cleaned["url"]
        self._plan = tuple(
            (name, cleaned[name]) for name in self.OPTIONAL_FIELDS if name in cleaned
        )
        self._flag_fields = tuple(f for f in self.FLAG_FIELDS if f in cleaned)

    # ------------------------------------------------------------------ init helpers

    @staticmethod
    def _validate_selector_shapes(selectors: dict[str, str]) -> None:
        if "::" in selectors["item"]:
            raise ValueError("'item' selector must select elements (no '::')")

        if not _ATTR_SELECTOR_RE.search(selectors["url"]):
            raise ValueError("'url' selector must end with ::attr(...)")

        for name, selector in selectors.items():
            if name in {"item", "url", "description"}:
                continue
            if name in {"raw_address", "raw_area"} and "::" not in selector:
                continue
            if not _VALUE_SELECTOR_RE.search(selector):
                raise ValueError(
                    f"Selector '{name}' must end with ::text or ::attr(...), "
                    f"got {selector!r}"
                )

    @staticmethod
    def _normalize_domains(allowed_domains: list[str]) -> frozenset[str]:
        if not isinstance(allowed_domains, list) or not allowed_domains:
            raise ValueError("allowed_domains must be a non-empty list")

        domains: set[str] = set()
        for domain in allowed_domains:
            if not isinstance(domain, str) or not domain.strip():
                raise ValueError("Each allowed domain must be non-empty")

            normalized = domain.strip().lower().rstrip(".")
            try:
                # Internationalised names -> punycode, as urlsplit returns them.
                normalized = normalized.encode("idna").decode("ascii")
            except UnicodeError as exc:
                raise ValueError(f"Invalid allowed domain: {domain!r}") from exc

            if len(normalized) > 253 or not _HOST_RE.match(normalized):
                raise ValueError(f"Invalid allowed domain: {domain!r}")
            domains.add(normalized)

        return frozenset(domains)

    # ------------------------------------------------------------------ extraction

    @staticmethod
    def _clean(value: str) -> str:
        return " ".join(value.split())

    def _first_value(self, scope: Selector, selector: str) -> str | None:
        item_attribute = _ITEM_ATTR_SELECTOR_RE.fullmatch(selector)
        if item_attribute:
            value = scope.attrib.get(item_attribute.group(1))
            return self._clean(value) if value else None
        elements = scope.xpath(selector) if selector.startswith(('//', './/')) else scope.css(selector)
        for value in elements.getall():
            cleaned = self._clean(value)
            if cleaned:
                return cleaned
        return None

    def _text_content(self, scope: Selector, selector: str) -> str | None:
        if "::" in selector:
            # Selector already yields text nodes / attributes.
            text = " ".join(scope.css(selector).getall())
        else:
            element = scope.css(selector)[:1]
            if not element:
                return None
            text = " ".join(element.xpath(".//text()").getall())
        return self._clean(text) or None

    def _extract_values(self, item: Selector) -> dict[str, str | None]:
        values: dict[str, str | None] = dict.fromkeys(self.OPTIONAL_FIELDS)
        for name, selector in self._plan:
            if name == "description" or (name in {"raw_address", "raw_area"} and "::" not in selector):
                values[name] = self._text_content(item, selector)
            else:
                values[name] = self._first_value(item, selector)
        return values

    # ------------------------------------------------------------------ URL handling

    def _is_allowed_host(self, host: str) -> bool:
        host = host.lower().rstrip(".")
        return host in self.allowed_domains or host.endswith(self._domain_suffixes)

    def _normalize_listing_url(
        self,
        response: TextResponse,
        raw_url: str | None,
    ) -> str:
        if not raw_url:
            raise ListingParseError("Listing URL is missing")

        parsed = urlsplit(urljoin(response.url, raw_url))

        if parsed.scheme.lower() not in {"http", "https"}:
            raise ListingParseError("Unsupported URL scheme")
        if not parsed.hostname:
            raise ListingParseError("URL has no hostname")
        try:
            _ = parsed.port  # raises ValueError on malformed port
        except ValueError as exc:
            raise ListingParseError("URL has an invalid port") from exc
        if parsed.username is not None or parsed.password is not None:
            raise ListingParseError("URL must not contain credentials")
        if not self._is_allowed_host(parsed.hostname):
            raise ListingParseError("URL host is outside allowed_domains")

        # Fragments are browser positions, not distinct listings.
        return parsed._replace(fragment="").geturl()

    # ------------------------------------------------------------------ parsing

    def _build(
        self,
        response: TextResponse,
        item: Selector,
        url: str,
        values: dict[str, str | None],
    ) -> ParsedListing:
        payload = item.get()
        if self.max_payload_chars is not None:
            payload = payload[: self.max_payload_chars]

        flags = tuple(f"missing_{n}" for n in self._flag_fields if not values[n])

        return ParsedListing(
            source=self.source,
            url=url,
            url_hash=create_url_hash(url),
            raw_payload=payload,
            page_url=response.url,
            quality_flags=flags,
            **values,
        )

    def parse_with_stats(
        self,
        response: TextResponse,
    ) -> tuple[list[ParsedListing], ParserStats]:
        """Parse a page and return (listings, stats). Holds no instance state."""
        results: list[ParsedListing] = []
        scores: list[int] = []
        index_by_url: dict[str, int] = {}

        items_found = invalid_url = duplicate_url = 0

        for item in response.css(self._item_selector):
            items_found += 1

            try:
                url = self._normalize_listing_url(
                    response,
                    self._first_value(item, self._url_selector),
                )
            except ListingParseError as exc:
                invalid_url += 1
                logger.debug("Invalid listing URL on %s: %s", response.url, exc)
                continue

            values = self._extract_values(item)
            score = sum(1 for v in values.values() if v)

            idx = index_by_url.get(url)
            if idx is None:
                index_by_url[url] = len(results)
                scores.append(score)
                results.append(self._build(response, item, url, values))
                continue

            duplicate_url += 1
            if score > scores[idx]:  # keep the more complete duplicate
                scores[idx] = score
                results[idx] = self._build(response, item, url, values)

        stats = ParserStats(items_found, len(results), invalid_url, duplicate_url)

        if items_found == 0:
            logger.warning(
                "No listing containers matched %r on %s (source=%s); "
                "the site layout may have changed",
                self._item_selector,
                response.url,
                self.source,
            )
        elif not results:
            logger.warning(
                "All %d listings on %s were rejected (source=%s)",
                items_found,
                response.url,
                self.source,
            )
        elif invalid_url or duplicate_url:
            logger.info(
                "source=%s page=%s found=%d parsed=%d invalid_url=%d duplicate_url=%d",
                self.source,
                response.url,
                items_found,
                len(results),
                invalid_url,
                duplicate_url,
            )

        return results, stats

    def parse(self, response: TextResponse) -> list[ParsedListing]:
        return self.parse_with_stats(response)[0]