from __future__ import annotations
import logging
from typing import Any
from pymongo import MongoClient, ReplaceOne
from pymongo.collection import Collection
from pymongo.errors import PyMongoError
from src.infrastructure.messaging.raw_event_envelope import (
    deserialize_raw_event_envelope,
)
from pymongo.errors import ConnectionFailure, ExecutionTimeout
from src.application.exceptions.transient_processing_error import TransientProcessingError
logger = logging.getLogger(__name__)
class MongoRawEventWriter:
    """Persists raw envelopes in batches using raw_event_id as an idempotency key."""

    def __init__(
        self,
        *,
        mongo_uri: str,
        database: str,
        collection: str = "raw_events",
        client: Any | None = None,
    ) -> None:
        if not mongo_uri.strip():
            raise ValueError("mongo_uri must not be blank")
        if not database.strip() or not collection.strip():
            raise ValueError("database and collection must not be blank")

        self._client = client or MongoClient(mongo_uri, maxPoolSize=5, minPoolSize=1)
        self._collection: Collection = self._client[database.strip()][collection.strip()]
        self._collection.create_index("crawl_run_id")
        self._collection.create_index("listing_key")

    def handle_batch(self, messages: list[Any]) -> None:
        """Validates and bulk-upserts a batch of Kafka messages using atomic operations."""
        if not messages:
            return

        bulk_operations = []

        for message in messages:
            if message.value() is None:
                logger.warning(f"Received empty Kafka message at partition={message.partition()} offset={message.offset()}")
                continue

            try:
                envelope = deserialize_raw_event_envelope(message.value())
                raw_event_id = envelope["raw_event_id"]
                bulk_operations.append(
                    ReplaceOne(
                        filter={"_id": raw_event_id},
                        replacement={
                            "_id": raw_event_id,
                            **envelope,
                            "kafka": {
                                "topic": message.topic(),
                                "partition": message.partition(),
                                "offset": message.offset(),
                            },
                        },
                        upsert=True
                    )
                )
            except Exception as e:
                logger.error(f"Error parsing raw event envelope context: {e}")
                raise

        if not bulk_operations:
            return

        try:
            self._collection.bulk_write(bulk_operations, ordered=False)
            logger.info(f"Successfully bulk-upserted {len(bulk_operations)} raw events into MongoDB.")
        except (ConnectionFailure, ExecutionTimeout) as conn_exc:
            raise TransientProcessingError(f"MongoDB is unavailable: {conn_exc}") from conn_exc
        except PyMongoError as exc:
                    raise RuntimeError(f"Failed to execute batch bulk_write on MongoDB: {exc}") from exc
    def close(self) -> None:
        """Close the MongoDB connection pool gracefully."""
        self._client.close()
