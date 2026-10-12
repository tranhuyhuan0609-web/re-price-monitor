from datetime import datetime, timezone

import pytest

from src.domain.entities.raw_event import (
    RawEvent,
    RawEventBuildError,
)


def make_raw_event(**overrides):
    data = {
        "raw_event_id": "event-001",
        "source": "example",
        "url": "https://example.com/listing/123",
        "crawl_run_id": "run-001",
        "crawled_at": datetime.now(timezone.utc),
        "parser_version": "1.0.0",
    }
    data.update(overrides)
    return RawEvent(**data)


def test_parser_version_cannot_be_omitted():
    data = {
        "raw_event_id": "event-001",
        "source": "example",
        "url": "https://example.com/listing/123",
        "crawl_run_id": "run-001",
        "crawled_at": datetime.now(timezone.utc),
    }

    with pytest.raises(TypeError):
        RawEvent(**data)


def test_parser_version_cannot_be_blank():
    with pytest.raises(RawEventBuildError):
        make_raw_event(parser_version="")


def test_parser_version_accepts_valid_value():
    event = make_raw_event(parser_version="1.0.0")

    assert event.parser_version == "1.0.0"
