from __future__ import annotations

from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection

from src.infrastructure.messaging.raw_event_envelope import (
    deserialize_raw_event_envelope,
)


class MongoRawEventWriter:
    """Persist raw envelopes with raw_event_id as an idempotency key."""

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

        self._client = client or MongoClient(mongo_uri)
        self._collection: Collection = self._client[database.strip()][collection.strip()]
        self._collection.create_index("crawl_run_id")
        self._collection.create_index("listing_key")

    def handle(self, message: Any) -> None:
        """Validate and upsert one Kafka message."""
        if message.value() is None:
            raise ValueError("Kafka message value must not be null")
        envelope = deserialize_raw_event_envelope(message.value())
        raw_event_id = envelope["raw_event_id"]
        self._collection.replace_one(
            {"_id": raw_event_id},
            {
                "_id": raw_event_id,
                **envelope,
                "kafka": {
                    "topic": message.topic(),
                    "partition": message.partition(),
                    "offset": message.offset(),
                },
            },
            upsert=True,
        )

    def close(self) -> None:
        self._client.close()
