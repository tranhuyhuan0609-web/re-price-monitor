from __future__ import annotations

from psycopg import connect

from src.infrastructure.config.settings import load_settings
from src.infrastructure.messaging.kafka_consumer import KafkaMessageConsumer
from src.infrastructure.postgres.raw_event_clean_processor import (
    RawEventCleanProcessor,
)
from src.infrastructure.postgres.exchange_rate_provider import (
    PostgresExchangeRateProvider,
)


def run_clean_event_consumer(*, max_messages: int | None = None) -> int:
    settings = load_settings()
    with connect(settings.postgres_dsn, autocommit=True) as connection:
        processor = RawEventCleanProcessor(
            connection,
            exchange_rate_provider=PostgresExchangeRateProvider(connection),
        )
        consumer = KafkaMessageConsumer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_GROUP_CLEAN_PROCESSOR,
            topics=[settings.KAFKA_RAW_TOPIC],
            handler=processor,
            dlq_bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            dlq_topic=settings.KAFKA_DLQ_TOPIC,
           
        )
        try:
            return consumer.run(max_messages=max_messages)
        finally:
            consumer.close()


if __name__ == "__main__":
    print(run_clean_event_consumer())
