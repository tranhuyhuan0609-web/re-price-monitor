from __future__ import annotations

from collections.abc import Callable, Mapping

from .base import DetailExtractor
from .css_extractor import CssDetailExtractor
from .meeyland_astro_extractor import MeeylandAstroExtractor


_ExtractorFactory = Callable[[Mapping[str, str]], DetailExtractor]
_DETAIL_EXTRACTORS: dict[str, _ExtractorFactory] = {
    "css": CssDetailExtractor,
    "meeyland_astro": MeeylandAstroExtractor,
}


def create_detail_extractor(
    name: str | None,
    selectors: Mapping[str, str],
) -> DetailExtractor:
    """Construct an extractor by configured name, without site-id checks."""
    normalized_name = (name or "css").strip().lower()
    extractor_factory = _DETAIL_EXTRACTORS.get(normalized_name)
    if extractor_factory is None:
        supported = ", ".join(sorted(_DETAIL_EXTRACTORS))
        raise ValueError(
            f"Unknown detail extractor {normalized_name!r}; supported: {supported}"
        )
    return extractor_factory(selectors)
