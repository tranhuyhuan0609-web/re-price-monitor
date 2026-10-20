from __future__ import annotations
import logging
import re
from datetime import datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo
logger = logging.getLogger(__name__)

DEFAULT_DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
)

MIN_VALID_DATE = datetime(2000, 1, 1, tzinfo=timezone.utc)
FUTURE_TOLERANCE = timedelta(days=1)

_ISO_LIKE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}(?:[T ].*)?$"
)

_WEEKDAY_RE = re.compile(
    r"^\s*(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday"
    r"|thứ\s+(?:hai|ba|tư|năm|sáu|bảy)|chủ\s+nhật)\s*,?\s*",
    re.IGNORECASE,
)

_GMT_RE = re.compile(
    r"\(?\s*GMT\s*([+-])(\d{1,2})(?::?(\d{2}))?\s*\)?",
    re.IGNORECASE,
)

_GMT_MARKER_RE = re.compile(r"\bGMT\b", re.IGNORECASE)
_MULTI_SPACE_RE = re.compile(r"\s+")


def _extract_gmt_offset(value: str) -> tuple[str, tzinfo | None]:
    matches = list(_GMT_RE.finditer(value))
    has_gmt_marker = _GMT_MARKER_RE.search(value) is not None

    if not matches:
        if has_gmt_marker:
            raise ValueError("Invalid GMT offset.")
        return value, None

    if len(matches) != 1:
        raise ValueError("Multiple GMT offsets are not supported.")

    match = matches[0]
    sign, hours, minutes = match.groups()

    hours_i = int(hours)
    minutes_i = int(minutes or 0)

    if hours_i > 14 or minutes_i > 59:
        raise ValueError("GMT offset is out of range.")

    if hours_i == 14 and minutes_i != 0:
        raise ValueError("GMT offset cannot exceed 14:00.")

    delta = timedelta(hours=hours_i, minutes=minutes_i)
    offset = delta if sign == "+" else -delta
    parsed_tz = timezone(offset)

    cleaned = (
        value[:match.start()] + " " + value[match.end():]
    ).strip()

    return cleaned, parsed_tz
def _has_explicit_timezone(value: str) -> bool:
    if not _ISO_LIKE_RE.fullmatch(value):
        return False

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False

    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _clean(value: str) -> tuple[str, tzinfo | None]:
    value = _WEEKDAY_RE.sub("", value.strip())
    value, offset_tz = _extract_gmt_offset(value)
    value = _MULTI_SPACE_RE.sub(" ", value).strip(" ,")

    if value[-1:].upper() == "Z":
        value = value[:-1] + "+00:00"
    if offset_tz is not None and _has_explicit_timezone(value):
        parsed = datetime.fromisoformat(value)
        iso_offset = parsed.utcoffset()
        gmt_offset = offset_tz.utcoffset(None)
        if iso_offset != gmt_offset:
            raise ValueError(
                "Conflicting timezone information: "
                f"ISO offset {iso_offset} vs GMT offset {gmt_offset}"
            )

    return value, offset_tz
def _parse_datetime(
    value: str,
    formats: tuple[str, ...],
) -> datetime | None:
    if _ISO_LIKE_RE.fullmatch(value):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass

    for date_format in formats:
        try:
            return datetime.strptime(value, date_format)
        except ValueError:
            continue

    return None


def _log_invalid(
    reason: str,
    *,
    site_id: str | None,
    value: str,
) -> None:
    logger.warning(
        "published_at: %s site_id=%s value=%r",
        reason,
        site_id,
        value,
    )
def parse_published_at(
    value: str | None,
    source_tz: ZoneInfo,
    formats: tuple[str, ...] = DEFAULT_DATE_FORMATS,
    *,
    now: datetime | None = None,
    site_id: str | None = None,
) -> datetime | None:

    if not isinstance(source_tz, ZoneInfo):
        raise TypeError("source_tz must be a ZoneInfo instance.")

    if now is not None:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("now must be timezone-aware.")

        current = now.astimezone(timezone.utc)
    else:
        current = datetime.now(timezone.utc)

    if value is None or not value.strip():
        return None

    try:
        cleaned, offset_tz = _clean(value)
    except ValueError:
        _log_invalid(
            "invalid timezone offset",
            site_id=site_id,
            value=value,
        )
        return None

    parsed = _parse_datetime(cleaned, formats) if cleaned else None

    if parsed is None:
        _log_invalid(
            "unparseable value",
            site_id=site_id,
            value=value,
        )
        return None

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=offset_tz or source_tz)

    try:
        result = parsed.astimezone(timezone.utc)
    except (OverflowError, ValueError):
        _log_invalid(
            "date out of range",
            site_id=site_id,
            value=value,
        )
        return None

    if result < MIN_VALID_DATE:
        _log_invalid(
            "date before minimum supported date",
            site_id=site_id,
            value=value,
        )
        return None

    if result > current + FUTURE_TOLERANCE:
        _log_invalid(
            "date too far in the future",
            site_id=site_id,
            value=value,
        )
        return None

    return result