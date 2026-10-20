from __future__ import annotations

from typing import Protocol

from scrapy.http import TextResponse


class DetailExtractor(Protocol):
    """Common interface for site-specific listing detail extraction."""

    @property
    def required_fields(self) -> tuple[str, ...]:
        """Fields that must be checked when deciding whether to fetch a detail page."""
        ...

    def extract_description(self, response: TextResponse) -> str | None:
        """Return the listing description, if available."""
        ...

    def extract_contact_info(self, response: TextResponse) -> str | None:
        """Return listing contact information, if available."""
        ...
