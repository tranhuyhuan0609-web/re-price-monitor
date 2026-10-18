from __future__ import annotations

import json
import logging
from confluent_kafka import Message
from pymongo import MongoClient
from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)

class MongoDLQEventWriter:
    """Handles parsing and writing DLQ messages into MongoDB."""

    def __init__(self, mongo_uri: str, database: str, collection_name: str) -> None:
        # Sử dụng chuỗi mongo_uri hoàn chỉnh (được sinh ra từ settings.mongo_uri)
        # Chuỗi này đã bao gồm user, password cấu hình sẵn authSource=admin
        self._client = MongoClient(mongo_uri)
        self._db = self._client[database]
        self._collection = self._db[collection_name]
        # Kiểm tra kết nối nhanh bằng lệnh ping
        self._client.admin.command("ping")

    def handle(self, message: Message) -> None:
        """This method matches the MessageHandler protocol required by KafkaMessageConsumer."""
        raw_value = message.value()
        if raw_value is None:
            logger.warning(f"Received empty DLQ message at offset {message.offset()}")
            return

        # Giải mã payload JSON của tin nhắn lỗi từ DLQ
        try:
            dlq_payload = json.loads(raw_value.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            dlq_payload = {
                "parse_error": "Could not decode UTF-8 or parse JSON",
                "raw_value_fallback": repr(raw_value)
            }

        # Tạo cấu trúc document lưu trữ kèm metadata
        document = {
            "dlq_metadata": {
                "topic": message.topic(),
                "partition": message.partition(),
                "offset": message.offset(),
                "timestamp": message.timestamp(),
                "key": message.key().decode("utf-8", errors="replace") if message.key() else None,
            },
            "error_payload": dlq_payload
        }

        try:
            self._collection.insert_one(document)
        except PyMongoError as exc:
            # Luôn ném lỗi ra ngoài để lớp KafkaMessageConsumer KHÔNG commit offset nhầm
            raise RuntimeError(f"Failed to insert DLQ event into MongoDB: {exc}") from exc

    def close(self) -> None:
        """Close MongoDB connection gracefully."""
        self._client.close()
