from __future__ import annotations

import os
from typing import Any

from scrapy import Spider

from src.domain.entities.raw_event import RawEvent
from src.infrastructure.messaging.kafka_raw_event_producer import (
    KafkaRawEventProducer,
    RawEventProducer,
)


class RawEventKafkaPipeline:
    """Publish every scraped RawEvent to Kafka and flush on spider close."""

    def __init__(
        self,
        producer: RawEventProducer,
    ) -> None:
        self._producer = producer

    @classmethod
    def from_crawler(cls, crawler) -> "RawEventKafkaPipeline":
        bootstrap_servers = crawler.settings.get(
            "KAFKA_BOOTSTRAP_SERVERS"
        ) or os.environ.get("KAFKA_BOOTSTRAP_SERVERS")
        topic = crawler.settings.get("KAFKA_RAW_TOPIC") or os.environ.get(
            "KAFKA_RAW_TOPIC"
        )

        if not bootstrap_servers:
            raise RuntimeError("KAFKA_BOOTSTRAP_SERVERS is not configured")
        if not topic:
            raise RuntimeError("KAFKA_RAW_TOPIC is not configured")

        return cls(
            KafkaRawEventProducer(
                bootstrap_servers=bootstrap_servers,
                topic=topic,
            )
        )

    def process_item(self, item: Any, spider: Spider) -> Any:
        if not isinstance(item, RawEvent):
            raise TypeError("RawEventKafkaPipeline accepts RawEvent only")

        self._producer.publish(item)
        return item

    def close_spider(self, spider: Spider) -> None:
        self._producer.close()
