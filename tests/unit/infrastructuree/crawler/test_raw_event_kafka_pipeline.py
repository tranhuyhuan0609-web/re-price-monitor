from datetime import datetime, timezone

import pytest

from src.domain.entities.raw_event import RawEvent
from src.infrastructure.crawler.pipelines.raw_event_kafka_pipeline import (
    RawEventKafkaPipeline,
)


class FakeProducer:
    def __init__(self):
        self.published = []
        self.closed = False

    def publish(self, event):
        self.published.append(event)

    def close(self):
        self.closed = True


def make_event():
    return RawEvent(
        raw_event_id="event-1",
        source="example",
        url="https://example.com/listing/1",
        crawl_run_id="run-1",
        crawled_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        parser_version="1.0.0",
    )


def test_pipeline_publishes_raw_events_and_flushes_on_close():
    producer = FakeProducer()
    pipeline = RawEventKafkaPipeline(producer)
    event = make_event()

    assert pipeline.process_item(event, spider=None) is event

    pipeline.close_spider(spider=None)

    assert producer.published == [event]
    assert producer.closed is True


def test_pipeline_rejects_non_raw_events():
    pipeline = RawEventKafkaPipeline(FakeProducer())

    with pytest.raises(TypeError, match="RawEvent only"):
        pipeline.process_item({"raw_event_id": "event-1"}, spider=None)
