from datetime import datetime, timezone

import pytest

from src.application.crawler.crawler_runner import (
    _validate_utc_datetime,
)


def test_validate_utc_datetime_converts_datetime_to_utc():
    value = datetime.fromisoformat("2026-10-16T15:00:00+07:00")

    result = _validate_utc_datetime(value, "started_at")

    assert result == datetime(
        2026, 10, 16, 8, 0, 0, tzinfo=timezone.utc
    )
    assert result.tzinfo == timezone.utc


def test_validate_utc_datetime_rejects_naive_datetime():
    value = datetime(2026, 10, 16, 8, 0, 0)

    with pytest.raises(ValueError, match="timezone-aware"):
        _validate_utc_datetime(value, "started_at")


def test_validate_utc_datetime_rejects_non_datetime():
    with pytest.raises(TypeError, match="must be a datetime"):
        _validate_utc_datetime("2026-10-16T08:00:00Z", "started_at")