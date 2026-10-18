from __future__ import annotations
from src.domain.entities.base import NonBlank, StrictBaseModel
import re
from typing import Literal
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

SITE_ID_RE = re.compile(r"[a-z0-9_-]+")
HOST_LABEL_RE = re.compile(
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
)

ALLOWED_PROXY_SCHEMES = frozenset({"http", "https", "socks5"})
def normalize_host(host: str | None) -> str:
    """Normalize a hostname for domain comparison."""
    if not host:
        raise ValueError("URL must have a hostname.")

    return host.lower().rstrip(".")

class StrictBaseModel(BaseModel):
    """Base model that rejects undeclared configuration fields."""

    model_config = ConfigDict(extra="forbid")

class Selectors(StrictBaseModel):
    """CSS selectors consumed by ListingParser."""

    item: NonBlank
    url: NonBlank

    source_listing_id: NonBlank | None = None
    title: NonBlank | None = None
    description: NonBlank | None = None
    raw_price: NonBlank | None = None
    raw_address: NonBlank | None = None
    raw_area: NonBlank | None = None
    contact_info: NonBlank | None = None

    def to_parser_dict(self) -> dict[str, str]:
        return self.model_dump(exclude_none=True)

class Pagination(StrictBaseModel):
    """Pagination configuration for a website."""

    enabled: bool = False
    next_page: NonBlank | None = None

    max_pages: int = Field(
        default=100,
        ge=1,
        description=(
            "Maximum page budget for a crawl run. "
            "The crawler must enforce this limit at runtime."
        ),
    )

    @model_validator(mode="after")
    def validate_pagination(self) -> Pagination:
        if self.enabled and self.next_page is None:
            raise ValueError(
                "next_page is required when pagination is enabled."
            )

        if not self.enabled and self.next_page is not None:
            raise ValueError(
                "next_page must be omitted when pagination is disabled."
            )

        return self
class ProxySettings(StrictBaseModel):
    """Proxy configuration with optional proxy rotation."""

    enabled: bool = False
    rotation_enabled: bool = False

    proxies: list[str] = Field(default_factory=list)

    max_failures: int = Field(
        default=3,
        ge=1,
    )

    cooldown_seconds: int = Field(
        default=60,
        ge=1,
    )

    @field_validator("proxies")
    @classmethod
    def validate_proxies(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []

        for value in values:
            value = value.strip()

            try:
                parts = urlsplit(value)
                scheme = parts.scheme.lower()
                hostname = parts.hostname
                port = parts.port
            except ValueError:
                raise ValueError("Invalid proxy URL.") from None

            if (
                scheme not in ALLOWED_PROXY_SCHEMES
                or not hostname
                or port is None
                or not 1 <= port <= 65535
            ):
                raise ValueError(
                    "Proxy URL must include an allowed scheme, "
                    "a hostname, and a valid port from 1 to 65535."
                )

            normalized.append(value)

        if len(normalized) != len(set(normalized)):
            raise ValueError(
                "Duplicate proxy URLs are not allowed."
            )

        return normalized

    @model_validator(mode="after")
    def validate_proxy_settings(self) -> ProxySettings:
        if self.rotation_enabled and not self.enabled:
            raise ValueError(
                "Proxy rotation requires enabled=True."
            )

        if self.enabled and not self.proxies:
            raise ValueError(
                "At least one proxy is required when proxy is enabled."
            )

        if self.rotation_enabled and len(self.proxies) < 2:
            raise ValueError(
                "Proxy rotation requires at least two proxies."
            )

        if not self.enabled and self.proxies:
            raise ValueError(
                "Proxy URLs must be empty when proxy is disabled."
            )

        return self


    def __repr__(self) -> str:
         return (
            "ProxySettings("
            f"enabled={self.enabled}, "
            f"rotation_enabled={self.rotation_enabled}, "
            f"proxy_count={len(self.proxies)}"
            ")"
        )

    __str__ = __repr__

class CrawlerSettings(StrictBaseModel):
    """Runtime settings for the Scrapy crawler."""

    delay: float = Field(
        default=1.0,
        gt=0.0,
    )

    randomize_delay: bool = True

    concurrent_requests: int = Field(
        default=1,
        ge=1,
        le=10,
    )

    download_timeout: float = Field(
        default=30.0,
        gt=0.0,
        le=300.0,
    )

    retry_enabled: bool = True

    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
    )

    @model_validator(mode="after")
    def validate_retry_settings(self) -> CrawlerSettings:
        if not self.retry_enabled and self.max_retries > 0:
            raise ValueError(
                "max_retries must be 0 when retry is disabled."
            )

        if self.retry_enabled and self.max_retries == 0:
            raise ValueError(
                "max_retries must be greater than 0 when retry is enabled."
            )

        return self


# ============================================================
# Crawler configuration
# ============================================================

class CrawlerConfig(StrictBaseModel):
    """Validated configuration for one crawl source."""

    site_id: NonBlank
    name: NonBlank
    enabled: bool
    schedule_interval_seconds: int = Field(
        default=3600,
        ge=60,
        description="Minimum interval between scheduled crawl runs.",
    )

    base_url: HttpUrl
    start_urls: list[HttpUrl] = Field(min_length=1)
    allowed_domains: list[str] = Field(min_length=1)

    selectors: Selectors
    pagination: Pagination
    crawler_settings: CrawlerSettings
    
    parser_version: str = "1.0.0"

    proxy_settings: ProxySettings = Field(
        default_factory=ProxySettings,
    )

    source_timezone: str = "UTC"
    @field_validator("site_id")
    @classmethod
    def validate_site_id(cls, value: str) -> str:
        value = value.lower()

        if not SITE_ID_RE.fullmatch(value):
            raise ValueError(
                "site_id may contain only a-z, 0-9, "
                "underscores, and hyphens."
            )

        return value

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("source_timezone")
    @classmethod
    def validate_source_timezone(cls, value: str) -> str:
        value = value.strip()

        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError, OSError):
            raise ValueError(
                f"Invalid source timezone: {value!r}"
            ) from None

        return value
    @field_validator("allowed_domains")
    @classmethod
    def normalize_allowed_domains(
        cls,
        values: list[str],
    ) -> list[str]:
        normalized: list[str] = []

        for value in values:
            domain = value.strip().lower().rstrip(".")

            if not domain or not all(
                HOST_LABEL_RE.fullmatch(label)
                for label in domain.split(".")
            ):
                raise ValueError(
                    f"Invalid hostname: {value!r}. "
                    "Use a plain ASCII hostname without scheme, "
                    "path, or port; convert IDNs to punycode."
                )

            normalized.append(domain)

        if len(normalized) != len(set(normalized)):
            raise ValueError(
                "Duplicate allowed domains are not allowed."
            )

        return normalized

    @field_validator("start_urls")
    @classmethod
    def validate_unique_start_urls(
        cls,
        values: list[HttpUrl],
    ) -> list[HttpUrl]:
        normalized_urls = [str(url) for url in values]

        if len(normalized_urls) != len(set(normalized_urls)):
            raise ValueError(
                "Duplicate start_urls are not allowed."
            )

        return values

    def is_allowed_domain(self, domain: str) -> bool:
        """Return whether a hostname matches the configured allowlist."""
        domain = normalize_host(domain)

        return any(
            domain == allowed
            or domain.endswith("." + allowed)
            for allowed in self.allowed_domains
        )

    @model_validator(mode="after")
    def validate_domains(self) -> CrawlerConfig:
        urls = [
            ("base_url", self.base_url),
            *[("start_url", url) for url in self.start_urls],
        ]

        for label, url in urls:
            hostname = normalize_host(url.host)

            if not self.is_allowed_domain(hostname):
                raise ValueError(
                    f"{label} hostname {hostname!r} "
                    "is not in allowed_domains."
                )

        return self
    @model_validator(mode="after")
    def validate_start_url_budget(self) -> CrawlerConfig:
        if len(self.start_urls) > self.pagination.max_pages:
            raise ValueError(
                f"Number of start_urls ({len(self.start_urls)}) "
                f"exceeds max_pages "
                f"({self.pagination.max_pages})."
            )

        return self
    def source_zoneinfo(self) -> ZoneInfo:
        return ZoneInfo(self.source_timezone)