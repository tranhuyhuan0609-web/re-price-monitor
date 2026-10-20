from __future__ import annotations

import json
from html import unescape
from typing import Any

from scrapy.http import TextResponse
from scrapy.selector import Selector

from .css_extractor import CssDetailExtractor


class MeeylandAstroExtractor(CssDetailExtractor):
    """Extract detail data from Meeyland HTML and serialized Astro props.

    This implementation intentionally lives outside RealEstateSpider so site-
    specific markup does not leak into crawl orchestration.
    """

    @property
    def required_fields(self) -> tuple[str, ...]:
        required = list(super().required_fields)
        # Contact may be encoded only in Astro component props, so a CSS
        # contact selector is not required for this source.
        if "contact_info" not in required:
            required.append("contact_info")
        return tuple(required)

    def extract_description(self, response: TextResponse) -> str | None:
        value = super().extract_description(response)
        if value:
            return value

        # First fallback: server-rendered description markup.
        for css in (
            "div.article-description .break-words",
            "div.article-description p",
        ):
            parts: list[str] = []
            for node in response.css(css):
                parts.extend(
                    node.xpath(
                        ".//text()[not(ancestor::script) and not(ancestor::style)]"
                    ).getall()
                )
            value = self._clean_parts(parts)
            if value:
                return value

        # Second fallback: Astro serializes some descriptions in component props.
        islands = response.css(
            'astro-island[component-url*="Description"][props]'
        )
        for island in islands:
            raw_props = island.attrib.get("props")
            if not raw_props:
                continue

            try:
                props = json.loads(raw_props)
            except (json.JSONDecodeError, TypeError):
                continue

            data_wrapper = props.get("data") if isinstance(props, dict) else None
            if (
                not isinstance(data_wrapper, list)
                or len(data_wrapper) < 2
                or not isinstance(data_wrapper[1], str)
            ):
                continue

            fragment = Selector(text=unescape(data_wrapper[1]))
            paragraphs = fragment.css("p")
            if paragraphs:
                parts = []
                for paragraph in paragraphs:
                    parts.extend(paragraph.xpath(".//text()").getall())
            else:
                parts = fragment.xpath("//text()").getall()

            value = self._clean_parts(parts)
            if value:
                return value

        # Last-resort summary; callers should not confuse it with full detail.
        meta_summary = response.css(
            'meta[name="description"]::attr(content)'
        ).get()
        return self._clean_parts([meta_summary or ""])

    def extract_contact_info(self, response: TextResponse) -> str | None:
        unique_phones: list[str] = []
        seen_article_ids: set[str] = set()

        for island in response.css(
            'astro-island[component-url*="PhoneNumber"][props]'
        ):
            raw_props = island.attrib.get("props")
            if not raw_props:
                continue

            try:
                props: Any = json.loads(raw_props)
            except (json.JSONDecodeError, TypeError):
                continue

            article_wrapper = props.get("article") if isinstance(props, dict) else None
            if (
                not isinstance(article_wrapper, list)
                or len(article_wrapper) < 2
                or not isinstance(article_wrapper[1], dict)
            ):
                continue

            article = article_wrapper[1]
            article_id_wrapper = article.get("_id")
            article_id = (
                article_id_wrapper[1]
                if isinstance(article_id_wrapper, list)
                and len(article_id_wrapper) > 1
                and isinstance(article_id_wrapper[1], str)
                else None
            )

            # The page can include duplicate responsive components for one article.
            if article_id and article_id in seen_article_ids:
                continue
            if article_id:
                seen_article_ids.add(article_id)

            contact_wrapper = article.get("contact")
            if (
                not isinstance(contact_wrapper, list)
                or len(contact_wrapper) < 2
                or not isinstance(contact_wrapper[1], dict)
            ):
                continue

            phones_wrapper = contact_wrapper[1].get("phones")
            if (
                not isinstance(phones_wrapper, list)
                or len(phones_wrapper) < 2
                or not isinstance(phones_wrapper[1], list)
            ):
                continue

            for entry in phones_wrapper[1]:
                if (
                    isinstance(entry, list)
                    and len(entry) > 1
                    and isinstance(entry[1], str)
                ):
                    phone = entry[1].strip()
                    if phone and phone not in unique_phones:
                        unique_phones.append(phone)

        return ", ".join(unique_phones) or None
