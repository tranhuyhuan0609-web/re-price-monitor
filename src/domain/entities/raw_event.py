from __future__ import annotations
import json
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol
from urllib.parse import quote, urlsplit, urlunsplit
from uuid import NAMESPACE_URL, uuid4, uuid5
from src.application.parsers.text_utils import remove_emoji_and_clean

_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_PERCENT_RE = re.compile(r"%[0-9a-fA-F]{2}")
_PATH_SAFE = "/%:@!$&'()*+,;=-._~"
_QUERY_SAFE = "/?%:@!$&'()*+,;=-._~"
_DEFAULT_PORTS = {"http": 80, "https": 443}

class RawEventBuildError(ValueError):
    """Raised when a Raw Event violates its contract."""

def _clean(value: str | None, field_name: str) -> str | None:
    """Strip a string and convert blank values to None."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise RawEventBuildError(
            f"{field_name} must be a string or None"
        )
    cleaned = remove_emoji_and_clean(value)
    return cleaned


def _require(value: str | None, field_name: str) -> str:
    """Return a non-empty, stripped string."""
    cleaned = _clean(value, field_name)
    if cleaned is None:
        raise RawEventBuildError(
            f"{field_name} must not be blank"
        )
    return cleaned


def _upper_percent(text: str) -> str:
    """Normalize percent-escape hex digits to uppercase."""
    return _PERCENT_RE.sub(lambda m: m.group().upper(), text)


def normalize_url(
    raw_url: str | None,
    field_name: str = "url",
) -> str:
    """
    Validate an absolute HTTP(S) URL and return its canonical form.

    - Lowercase scheme and hostname.
    - Convert IDN hostname to punycode.
    - Remove trailing hostname dot and default port.
    - Percent-encode spaces and non-ASCII path/query characters.
    - Uppercase existing percent escapes.
    - Replace an empty path with '/'.
    - Remove the fragment while preserving the query.
    """
    url = _require(raw_url, field_name)

    if _CONTROL_RE.search(url):
        raise RawEventBuildError(
            f"{field_name} must not contain control characters"
        )

    try:
        parsed = urlsplit(url)

        scheme = parsed.scheme.lower()
        if scheme not in _DEFAULT_PORTS:
            raise RawEventBuildError(
                f"{field_name} must use HTTP or HTTPS"
            )

        host = (parsed.hostname or "").rstrip(".")
        if not host:
            raise RawEventBuildError(
                f"{field_name} must contain a hostname"
            )

        port = parsed.port

        if parsed.username is not None or parsed.password is not None:
            raise RawEventBuildError(
                f"{field_name} must not contain credentials"
            )

        if not host.isascii():
            host = host.encode("idna").decode("ascii")

        host = host.lower()

    except RawEventBuildError:
        raise
    except (ValueError, UnicodeError) as exc:
        raise RawEventBuildError(
            f"{field_name} is malformed"
        ) from exc

    netloc = f"[{host}]" if ":" in host else host

    if port is not None and port != _DEFAULT_PORTS[scheme]:
        netloc = f"{netloc}:{port}"

    path = _upper_percent(
        quote(parsed.path, safe=_PATH_SAFE)
    ) or "/"

    query = _upper_percent(
        quote(parsed.query, safe=_QUERY_SAFE)
    )

    return urlunsplit((scheme, netloc, path, query, ""))


def deterministic_event_id(
    source: str,
    url: str,
    crawl_run_id: str,
) -> str:
    """
    Generate a stable ID for a listing URL within one crawl run.

    Same normalized inputs produce the same ID.
    """
    source = _require(source, "source").lower()
    url = normalize_url(url)
    crawl_run_id = _require(crawl_run_id, "crawl_run_id")

    identity = json.dumps(
        [source, url, crawl_run_id],
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return str(uuid5(NAMESPACE_URL, identity))


def _random_event_id(
    source: str,
    url: str,
    crawl_run_id: str,
) -> str:
    """Generate a new ID for each build."""
    return str(uuid4())


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_timestamp(value: datetime) -> datetime:
    """Require a timezone-aware datetime and normalize it to UTC."""
    if not isinstance(value, datetime):
        raise RawEventBuildError(
            "crawled_at must be a datetime"
        )

    if value.tzinfo is None or value.utcoffset() is None:
        raise RawEventBuildError(
            "crawled_at must be timezone-aware"
        )

    return value.astimezone(timezone.utc)


def _normalize_flags(
    flags: Sequence[str],
) -> tuple[str, ...]:
    """Validate, deduplicate, and sort quality flags."""
    if isinstance(flags, str) or not isinstance(flags, (tuple, list)):
        raise RawEventBuildError(
            "quality_flags must be a tuple or list of strings"
        )

    normalized = {
        _require(flag, "quality_flag")
        for flag in flags
    }

    return tuple(sorted(normalized))


def _lenient_page_url(value: str | None) -> str | None:
    """Invalid page_url metadata is dropped instead of rejecting the event."""
    try:
        return normalize_url(value, "page_url") if value is not None else None
    except RawEventBuildError:
        return None

class ListingLike(Protocol):
    """Structural interface for a parsed listing."""

    @property
    def source(self) -> str: ...

    @property
    def url(self) -> str: ...

    @property
    def title(self) -> str | None: ...

    @property
    def description(self) -> str | None: ...

    @property
    def raw_price(self) -> str | None: ...

    @property
    def raw_address(self) -> str | None: ...

    @property
    def raw_area(self) -> str | None: ...

    @property
    def contact_info(self) -> str | None: ...

    @property
    def raw_payload(self) -> dict[str, Any] | str | None: ...

    @property
    def page_url(self) -> str | None: ...

    @property
    def quality_flags(self) -> tuple[str, ...]: ...


_TEXT_FIELDS = (
    "title",
    "description",
    "raw_price",
    "raw_address",
    "raw_area",
    "contact_info",
)

@dataclass(frozen=True, slots=True)
class RawEvent:
    """Immutable event representing one listing observation."""

    raw_event_id: str
    source: str
    url: str
    crawl_run_id: str
    crawled_at: datetime


    parser_version: str

    title: str | None = None
    description: str | None = None
    raw_price: str | None = None
    raw_address: str | None = None
    raw_area: str | None = None
    contact_info: str | None = None

    raw_payload: dict[str, Any] | str | None = None
    page_url: str | None = None
    quality_flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        def put(name: str, value: Any) -> None:
            object.__setattr__(self, name, value)

        put(
            "raw_event_id",
            _require(self.raw_event_id, "raw_event_id"),
        )
        put(
            "source",
            _require(self.source, "source").lower(),
        )
        put(
            "crawl_run_id",
            _require(self.crawl_run_id, "crawl_run_id"),
        )
        put("url", normalize_url(self.url))
        put("crawled_at", _normalize_timestamp(self.crawled_at))
        put(
            "parser_version",
            _require(self.parser_version, "parser_version"),
        )

        for name in _TEXT_FIELDS:
            put(name, _clean(getattr(self, name), name))

        put("page_url", _lenient_page_url(self.page_url))
        put("quality_flags", _normalize_flags(self.quality_flags))

        if self.raw_payload is not None and not isinstance(
            self.raw_payload, (dict, str)
        ):
            raise RawEventBuildError(
                "raw_payload must be a dict, string, or None"
            )

class RawEventBuilder:
    """Build validated Raw Events from parsed listings."""

    def __init__(
        self,
        *,
        id_factory: Callable[[str, str, str], str] = _random_event_id,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        """
        id_factory(source, url, crawl_run_id) -> event ID.

        Default: random UUID.
        Use deterministic_event_id for stable IDs across retries.

        clock() supplies the timestamp when crawled_at is omitted.
        """
        self._id_factory = id_factory
        self._clock = clock

    def build(
        self,
        listing: ListingLike,
        crawl_run_id: str,
        *,
        parser_version: str,
        crawled_at: datetime | None = None,
    ) -> RawEvent:
        """Build one validated event from a parsed listing."""
        source = _require(listing.source, "source").lower()
        url = normalize_url(listing.url)
        run_id = _require(crawl_run_id, "crawl_run_id")

        event_id = _require(
            self._id_factory(source, url, run_id),
            "raw_event_id",
        )

        event_time = (
            crawled_at
            if crawled_at is not None
            else self._clock()
        )

        return RawEvent(
            raw_event_id=event_id,
            source=source,
            url=url,
            crawl_run_id=run_id,
            crawled_at=event_time,
            parser_version=parser_version,
            title=listing.title,
            description=listing.description,
            raw_price=listing.raw_price,
            raw_address=listing.raw_address,
            raw_area=listing.raw_area,
            contact_info=listing.contact_info,
            raw_payload=listing.raw_payload,
            page_url=listing.page_url,
            quality_flags=listing.quality_flags,
        )
