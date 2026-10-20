from __future__ import annotations
import logging
import json
from typing import Any, Protocol
from confluent_kafka import (
    Consumer,
    KafkaError,
    KafkaException,
    Message,
    Producer,
)

logger = logging.getLogger(__name__)

class MessageHandlerBatch(Protocol):
    """Protocol for processors that handle bulk message arrays instead of single items."""
    def handle_batch(self, messages: list[Message]) -> None:
        ...

class KafkaConsumerError(RuntimeError):
    """Raised when consuming or processing a Kafka message fails."""

class KafkaMessageConsumer:
    """Consumes messages in batches and commits offsets explicitly following database confirmations."""

    def __init__(
        self,
        *,
        bootstrap_servers: str,
        group_id: str,
        topics: list[str],
        handler: MessageHandlerBatch,
        consumer: Any | None = None,
        poll_timeout: float = 1.0,
        batch_size: int = 200,          
        dlq_bootstrap_servers: str | None = None,
        dlq_topic: str | None = None,
    ) -> None:
        if not bootstrap_servers.strip():
            raise ValueError("bootstrap_servers must not be blank")
        if not group_id.strip():
            raise ValueError("group_id must not be blank")
        if not topics or any(not topic.strip() for topic in topics):
            raise ValueError("topics must contain non-blank values")
        if poll_timeout <= 0:
            raise ValueError("poll_timeout must be positive")
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if (dlq_bootstrap_servers is None) != (dlq_topic is None):
            raise ValueError(
                "dlq_bootstrap_servers and dlq_topic must be configured together"
            )
        if dlq_topic is not None and not dlq_topic.strip():
            raise ValueError("dlq_topic must not be blank")

        self._poll_timeout = poll_timeout
        self._batch_size = batch_size
        self._handler = handler
        self._closed = False
        self._running = True  
        
        self._dlq_topic = dlq_topic.strip() if dlq_topic else None
        self._dlq_producer = (
            Producer({"bootstrap.servers": dlq_bootstrap_servers.strip()})
            if dlq_bootstrap_servers and dlq_topic
            else None
        )

        self._consumer = consumer or Consumer(
            {
                "bootstrap.servers": bootstrap_servers.strip(),
                "group.id": group_id.strip(),
                "enable.auto.commit": False,
                "enable.auto.offset.store": False,
                "auto.offset.reset": "earliest",
                "session.timeout.ms": 40000,
                "max.poll.interval.ms": 300000,
            }
        )
        self._consumer.subscribe([topic.strip() for topic in topics])

    def run(self, *, max_messages: int | None = None) -> int:
        """Processes messages in batches until stopped or max_messages thresholds are fulfilled."""
        if max_messages is not None and max_messages <= 0:
            raise ValueError("max_messages must be positive when provided")

        processed = 0
        self._running = True
        msg_buffer: list[Message] = []  

        while self._running and (max_messages is None or processed < max_messages):
            if self._dlq_producer is not None:
                self._dlq_producer.poll(0)

            message = self._consumer.poll(self._poll_timeout)
            
            if message is None:
                # Timeout hit (idle stream) -> Immediately flush remaining cached buffer contents to avoid delays
                if msg_buffer:
                    self._dispatch_batch(msg_buffer)
                    processed += len(msg_buffer)
                    msg_buffer = []
                continue

            if message.error() is not None:
                if message.error().code() == KafkaError._PARTITION_EOF:
                    continue
                raise KafkaConsumerError(f"Kafka poll failed: {message.error()}")

            msg_buffer.append(message)

            if len(msg_buffer) >= self._batch_size:
                self._dispatch_batch(msg_buffer)
                processed += len(msg_buffer)
                msg_buffer = []

        if msg_buffer:
            self._dispatch_batch(msg_buffer)
            processed += len(msg_buffer)

        return processed

    def _dispatch_batch(self, batch: list[Message]) -> None:
        """Executes handler batch processing and manages atomic offset commits."""
        try:
            self._handler.handle_batch(batch)
            self._consumer.commit(message=batch[-1], asynchronous=False)
        except Exception as exc:
            logger.warning("Bulk batch insert failed. Falling back to row-by-row recovery strategy...")
            
            # Fallback Recovery: Fall back to executing single-item workflows to secure poison pills
            for message in batch:
                try:
                    self._handler.handle_batch([message])
                    self._consumer.commit(message=message, asynchronous=False)
                except Exception as row_exc:
                    logger.exception(
                        "Kafka message processing failed persistently topic=%s partition=%s offset=%s",
                        message.topic(), message.partition(), message.offset(),
                    )
                    if self._dlq_producer is None or self._dlq_topic is None:
                        raise KafkaConsumerError("Persistent message failure occurred but DLQ is not configured") from row_exc
                    
                    # Push single corrupt item to DLQ and advance the commit offset to keep partition alive
                    self._publish_dlq(message, row_exc)
                    self._consumer.commit(message=message, asynchronous=False)

    def _publish_dlq(self, message: Message, error: Exception) -> None:
        """Asynchronously dispatches execution context errors to the destination DLQ pipeline."""
        payload = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "source_topic": message.topic(),
            "source_partition": message.partition(),
            "source_offset": message.offset(),
            "value": (message.value().decode("utf-8", errors="replace") if message.value() is not None else None),
        }
        try:
            self._dlq_producer.produce(
                topic=self._dlq_topic,
                key=message.key(),
                value=json.dumps(payload, ensure_ascii=True),
            )
        except KafkaException as exc:
            raise KafkaConsumerError("Kafka DLQ publish failed") from exc

    def close(self) -> None:
        if self._closed:
            return
        try:
            self._running = False  
            self._consumer.unsubscribe()
            self._consumer.close()
            if self._dlq_producer is not None:
                self._dlq_producer.flush(10.0)
        except KafkaException as exc:
            raise KafkaConsumerError("Kafka consumer close failed") from exc
        finally:
            self._closed = True
