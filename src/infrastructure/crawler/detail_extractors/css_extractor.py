from __future__ import annotations
import re
from html import unescape
from typing import Mapping
import emoji
from scrapy.http import TextResponse


_TEXT_SUFFIX_RE = re.compile(r"\s*::text\s*$")
_WHITESPACE_RE = re.compile(r"[ \t]+")


class CssDetailExtractor:
    """Extract and clean detail fields using configured selectors."""

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

       
        _EMOJI_RE = re.compile(
            "["
            "\\U0001F600-\\U0001F64F",
            "\\U0001F300-\\U0001F5FF",
            "\\U0001F680-\\U0001F6FF",
            "\\U0001F900-\\U0001F9FF",
            "\\U0001FA70-\\U0001FAFF",
            "\\U00002700-\\U000027BF", 
            "\\U0001F1E6-\\U0001F1FF",
            flags=re.UNICODE
        )
        
        _TRUNCATED_RE = re.compile(r"(\w+)&…")

        for part in parts:
            text = unescape(part)
            
            text = _EMOJI_RE.sub("", text)
            
    
            text = _TRUNCATED_RE.sub(r"\1", text)
            
            text = _WHITESPACE_RE.sub(" ", text).strip()

            if not text or text in ignored_labels:
                continue

            if not cleaned or cleaned[-1] != text:
                cleaned.append(text)

        result = "\n".join(cleaned).strip()
        return result or None

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