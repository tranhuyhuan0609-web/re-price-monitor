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
        if (dlq_bootstrap_servers is None) != (dlq_topic is None):
            raise ValueError(
                "dlq_bootstrap_servers and dlq_topic must be configured together"
            )
        if dlq_topic is not None and not dlq_topic.strip():
            raise ValueError("dlq_topic must not be blank")

        self._poll_timeout = poll_timeout
        self._handler = handler
        self._closed = False
        self._running = True  # Cờ kiểm soát luồng chạy ngầm để stop an toàn
        
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
        self._running = True

        # Vòng lặp kiểm tra thêm cờ chạy _running để hỗ trợ dừng ứng dụng mượt mà
        while self._running and (max_messages is None or processed < max_messages):
            
            # Kích hoạt poll Producer định kỳ giải phóng hàng đợi sự kiện của DLQ
            if self._dlq_producer is not None:
                self._dlq_producer.poll(0)

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
                
                if self._dlq_producer is None or self._dlq_topic is None:
                    raise KafkaConsumerError(
                        "Kafka message processing failed"
                    ) from exc
                
                self._publish_dlq(message, exc)
                # Commit offset sau khi đẩy vào DLQ thành công để tránh lặp tin nhắn lỗi vô hạn
                self._consumer.commit(message=message, asynchronous=False)

            processed += 1

        return processed

    def _publish_dlq(self, message: Message, error: Exception) -> None:
        payload = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "source_topic": message.topic(),
            "source_partition": message.partition(),
            "source_offset": message.offset(),
            "value": (
                message.value().decode("utf-8", errors="replace")
                if message.value() is not None
                else None
            ),
        }
        try:
            # Gửi bất đồng bộ (Asynchronous), không block luồng xử lý chính
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
            self._running = False  # Đánh dấu dừng vòng lặp run()
            self._consumer.unsubscribe()
            self._consumer.close()
            
            # Đợi tối đa 10s dọn sạch các tin nhắn DLQ còn sót lại trong hàng đợi trước khi tắt hẳn
            if self._dlq_producer is not None:
                self._dlq_producer.flush(10.0)
        except KafkaException as exc:
            raise KafkaConsumerError("Kafka consumer close failed") from exc
        finally:
            self._closed = True
