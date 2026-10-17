from unittest.mock import Mock, patch

from src.infrastructure.messaging.raw_event_consumer import (
    run_raw_event_consumer,
)


def test_run_raw_event_consumer_closes_resources():
    settings = Mock(
        mongo_uri="mongodb://localhost:27017",
        MONGO_DB="realestate_raw",
        KAFKA_BOOTSTRAP_SERVERS="localhost:9092",
        KAFKA_GROUP_RAW_WRITER="raw-writer",
        KAFKA_RAW_TOPIC="realestate.raw.v1",
    )
    writer = Mock()
    consumer = Mock()
    consumer.run.return_value = 1

    with (
        patch(
            "src.infrastructure.messaging.raw_event_consumer.load_settings",
            return_value=settings,
        ),
        patch(
            "src.infrastructure.messaging.raw_event_consumer.MongoRawEventWriter",
            return_value=writer,
        ),
        patch(
            "src.infrastructure.messaging.raw_event_consumer.KafkaMessageConsumer",
            return_value=consumer,
        ),
    ):
        assert run_raw_event_consumer(max_messages=1) == 1

    consumer.close.assert_called_once()
    writer.close.assert_called_once()
