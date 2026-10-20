from __future__ import annotations
import logging
from typing import Any, Protocol
from confluent_kafka import KafkaException, Producer
from src.domain.entities.raw_event import RawEvent
from src.infrastructure.messaging.raw_event_envelope import (
    serialize_raw_event,
)

logger = logging.getLogger(__name__)


class RawEventProducer(Protocol):
    def publish(self, event: RawEvent) -> None:
        ...

    def close(self) -> None:
        ...


class KafkaPublishError(RuntimeError):
    """Raised when Kafka rejects a raw event or cannot flush delivery."""


class KafkaRawEventProducer:
    """Confluent Kafka producer for versioned RawEvent envelopes."""

    def __init__(
        self,
        *,
        bootstrap_servers: str,
        topic: str,
        producer: Any | None = None,
        flush_timeout: float = 10.0,
    ) -> None:
        if not bootstrap_servers.strip():
            raise ValueError("bootstrap_servers must not be blank")
        if not topic.strip():
            raise ValueError("topic must not be blank")
        if flush_timeout <= 0:
            raise ValueError("flush_timeout must be positive")

        self._topic = topic.strip()
        self._flush_timeout = flush_timeout
        self._delivery_error: KafkaException | None = None
        self._producer = producer or Producer(
            {
                "bootstrap.servers": bootstrap_servers.strip(),
                "acks": "all",
                "enable.idempotence": True,
            }
        )

    @property
    def topic(self) -> str:
        return self._topic

    def _delivery_callback(self, error: KafkaException | None, message) -> None:
        if error is not None:
            self._delivery_error = error
            logger.error(
                "Kafka delivery failed topic=%s key=%s error=%s",
                self._topic,
                message.key(),
                error,
            )

    def publish(self, event: RawEvent) -> None:
        if not isinstance(event, RawEvent):
            raise TypeError("event must be a RawEvent")

        try:
            self._producer.produce(
                topic=self._topic,
                key=event.raw_event_id.encode("utf-8"),
                value=serialize_raw_event(event),
                on_delivery=self._delivery_callback,
            )
            self._producer.poll(0)
        except BufferError as exc:
            raise KafkaPublishError(
                "Kafka producer queue is full"
            ) from exc
        except KafkaException as exc:
            raise KafkaPublishError("Kafka publish failed") from exc

    def close(self) -> None:
        remaining = self._producer.flush(self._flush_timeout)
        if remaining:
            raise KafkaPublishError(
                f"{remaining} Kafka message(s) were not delivered "
                f"within {self._flush_timeout} seconds"
            )
        if self._delivery_error is not None:
            error = self._delivery_error
            self._delivery_error = None
            raise KafkaPublishError("Kafka delivery failed") from error
