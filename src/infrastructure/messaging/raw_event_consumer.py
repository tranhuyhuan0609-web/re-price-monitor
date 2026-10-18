from __future__ import annotations

import logging

from src.infrastructure.config.settings import load_settings
from src.infrastructure.database.mongo_raw_event_writer import MongoRawEventWriter
from src.infrastructure.messaging.kafka_consumer import KafkaMessageConsumer

logger = logging.getLogger(__name__)


def run_raw_event_consumer(*, max_messages: int | None = None) -> int:
    """Run the raw-event consumer using the application configuration."""
    settings = load_settings()
    writer = MongoRawEventWriter(
        mongo_uri=settings.mongo_uri,
        database=settings.MONGO_DB,
    )
    consumer = KafkaMessageConsumer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=settings.KAFKA_GROUP_RAW_WRITER,
        topics=[settings.KAFKA_RAW_TOPIC],
        handler=writer,
        dlq_bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        dlq_topic=settings.KAFKA_DLQ_TOPIC,
    )
    try:
        return consumer.run(max_messages=max_messages)
    finally:
        consumer.close()
        writer.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_raw_event_consumer()
