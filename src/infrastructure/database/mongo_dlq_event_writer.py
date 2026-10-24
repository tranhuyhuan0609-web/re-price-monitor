from __future__ import annotations
from src.application.exceptions.transient_processing_error import TransientProcessingError
import json
import logging
from confluent_kafka import Message
from pymongo import MongoClient
from pymongo.errors import PyMongoError,ConnectionFailure, ExecutionTimeout
logger = logging.getLogger(__name__)

class MongoDLQEventWriter:
    """Handles parsing and writing DLQ messages into MongoDB in performance-optimized bulk batches."""

    def __init__(self, mongo_uri: str, database: str, collection_name: str) -> None:
        # Connect using the full mongo_uri containing string authentication properties
        self._client = MongoClient(mongo_uri, maxPoolSize=5, minPoolSize=1)
        self._db = self._client[database]
        self._collection = self._db[collection_name]
        # Perform a fast connection check
        self._client.admin.command("ping")

    def handle_batch(self, messages: list[Message]) -> None:
        """Processes an array of Kafka messages and executes an efficient bulk insert operation."""
        if not messages:
            return

        documents_to_insert = []

        for message in messages:
            raw_value = message.value()
            if raw_value is None:
                logger.warning(f"Received empty DLQ message at partition={message.partition()} offset={message.offset()}")
                continue

            # Parse the incoming raw DLQ JSON payload safely
            try:
                dlq_payload = json.loads(raw_value.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                dlq_payload = {
                    "parse_error": "Could not decode UTF-8 string or parse standard JSON formatting rules",
                    "raw_value_fallback": repr(raw_value)
                }

            # Map fields into a structured MongoDB document template
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
            documents_to_insert.append(document)

        if not documents_to_insert:
            return

        try:
            # ordered=False allows parallel insertions and prevents a single bad document from halting the batch
            self._collection.insert_many(documents_to_insert, ordered=False)
            logger.info(f"Successfully flushed a bulk batch of {len(documents_to_insert)} error records to MongoDB.")
        except (ConnectionFailure, ExecutionTimeout) as conn_exc:
            # Raise a transient processing error to signal the consumer to retry the batch later
            raise TransientProcessingError(f"MongoDB is unavailable: {conn_exc}") from conn_exc
        except PyMongoError as exc:
                    # Raise exception outward to ensure the Kafka consumer safely handles the error context and holds offsets
                    raise RuntimeError(f"Failed to execute batch insertion of DLQ events into MongoDB: {exc}") from exc

    def close(self) -> None:
        """Close the MongoDB connection pool gracefully."""
        self._client.close()
