from __future__ import annotations
import re
from html import unescape
from typing import Mapping
from scrapy.http import TextResponse


_TEXT_SUFFIX_RE = re.compile(r"\s*::text\s*$")


class CssDetailExtractor:
    """Extract detail fields using selectors supplied by crawler configuration."""

    def __init__(self, selectors: Mapping[str, str]) -> None:
        self._selectors = dict(selectors)

    @property
    def required_fields(self) -> tuple[str, ...]:
        return tuple(
            field
            for field in ("description", "contact_info")
            if self._selectors.get(field)
        )

    @staticmethod
    def _clean_parts(parts: list[str]) -> str | None:
        cleaned: list[str] = []
        ignored_labels = {"Xem thêm", "Thu gọn"}

        for part in parts:
            text = " ".join(unescape(part).split())
            if not text or text in ignored_labels:
                continue
            if not cleaned or cleaned[-1] != text:
                cleaned.append(text)

        return "\n".join(cleaned) or None

    def extract_description(self, response: TextResponse) -> str | None:
        selector = self._selectors.get("description")
        if not selector:
            return None

        try:
            if "::attr(" in selector:
                parts = response.css(selector).getall()
                return self._clean_parts(parts)

            element_selector = _TEXT_SUFFIX_RE.sub("", selector).strip()
            nodes = response.css(element_selector)
            parts: list[str] = []
            for node in nodes:
                parts.extend(
                    node.xpath(
                        ".//text()[not(ancestor::script) and not(ancestor::style)]"
                    ).getall()
                )
            return self._clean_parts(parts)
        except (ValueError, TypeError):
            # Invalid selectors should not crash the entire crawl. Validation
            # of the config remains the primary place to catch this problem.
            return None

    def extract_contact_info(self, response: TextResponse) -> str | None:
        selector = self._selectors.get("contact_info")
        if not selector:
            return None

        try:
            for value in response.css(selector).getall():
                cleaned = " ".join(value.split())
                if cleaned:
                    return cleaned
        except (ValueError, TypeError):
            return None

        return None
