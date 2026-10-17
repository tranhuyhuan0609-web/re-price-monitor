from __future__ import annotations

import logging
from typing import Any, Protocol

from confluent_kafka import Consumer, KafkaError, KafkaException, Message

logger = logging.getLogger(__name__)


class MessageHandler(Protocol):
    def handle(self, message: Message) -> None:
        ...


class KafkaConsumerError(RuntimeError):
    """Raised when consuming or processing a Kafka message fails."""


class KafkaMessageConsumer:
    """Consume messages and commit offsets only after successful processing."""

    def __init__(
        self,
        *,
        bootstrap_servers: str,
        group_id: str,
        topics: list[str],
        handler: MessageHandler,
        consumer: Any | None = None,
        poll_timeout: float = 1.0,
    ) -> None:
        if not bootstrap_servers.strip():
            raise ValueError("bootstrap_servers must not be blank")
        if not group_id.strip():
            raise ValueError("group_id must not be blank")
        if not topics or any(not topic.strip() for topic in topics):
            raise ValueError("topics must contain non-blank values")
        if poll_timeout <= 0:
            raise ValueError("poll_timeout must be positive")

        self._poll_timeout = poll_timeout
        self._handler = handler
        self._closed = False
        self._consumer = consumer or Consumer(
            {
                "bootstrap.servers": bootstrap_servers.strip(),
                "group.id": group_id.strip(),
                "enable.auto.commit": False,
                "enable.auto.offset.store": False,
                "auto.offset.reset": "earliest",
                "session.timeout.ms": 10000,
                "max.poll.interval.ms": 300000,
            }
        )
        self._consumer.subscribe([topic.strip() for topic in topics])

    def run(self, *, max_messages: int | None = None) -> int:
        """Process messages until stopped or max_messages have succeeded."""
        if max_messages is not None and max_messages <= 0:
            raise ValueError("max_messages must be positive when provided")

        processed = 0
        while max_messages is None or processed < max_messages:
            message = self._consumer.poll(self._poll_timeout)
            if message is None:
                continue
            if message.error() is not None:
                if message.error().code() == KafkaError._PARTITION_EOF:
                    continue
                raise KafkaConsumerError(
                    f"Kafka poll failed: {message.error()}"
                )

            try:
                self._handler.handle(message)
                self._consumer.commit(message=message, asynchronous=False)
            except Exception as exc:
                logger.exception(
                    "Kafka message processing failed topic=%s partition=%s offset=%s",
                    message.topic(),
                    message.partition(),
                    message.offset(),
                )
                raise KafkaConsumerError("Kafka message processing failed") from exc
            processed += 1
        return processed

    def close(self) -> None:
        if self._closed:
            return
        try:
            self._consumer.unsubscribe()
            self._consumer.close()
        except KafkaException as exc:
            raise KafkaConsumerError("Kafka consumer close failed") from exc
        finally:
            self._closed = True
