from unittest.mock import Mock

import pytest

from src.infrastructure.messaging.kafka_consumer import (
    KafkaConsumerError,
    KafkaMessageConsumer,
)


def _message() -> Mock:
    message = Mock()
    message.error.return_value = None
    message.topic.return_value = "realestate.raw.v1"
    message.partition.return_value = 0
    message.offset.return_value = 3
    return message


def test_consumer_commits_only_after_handler_succeeds():
    kafka_consumer = Mock()
    kafka_consumer.poll.side_effect = [_message()]
    handler = Mock()

    consumer = KafkaMessageConsumer(
        bootstrap_servers="localhost:9092",
        group_id="raw-writer",
        topics=["realestate.raw.v1"],
        handler=handler,
        consumer=kafka_consumer,
    )

    assert consumer.run(max_messages=1) == 1
    handler.handle.assert_called_once()
    kafka_consumer.commit.assert_called_once_with(
        message=handler.handle.call_args.args[0],
        asynchronous=False,
    )

    consumer.close()
    kafka_consumer.unsubscribe.assert_called_once()
    kafka_consumer.close.assert_called_once()
    consumer.close()
    assert kafka_consumer.close.call_count == 1


def test_consumer_does_not_commit_when_handler_fails():
    kafka_consumer = Mock()
    kafka_consumer.poll.side_effect = [_message()]
    handler = Mock()
    handler.handle.side_effect = ValueError("invalid event")

    consumer = KafkaMessageConsumer(
        bootstrap_servers="localhost:9092",
        group_id="raw-writer",
        topics=["realestate.raw.v1"],
        handler=handler,
        consumer=kafka_consumer,
    )

    with pytest.raises(KafkaConsumerError):
        consumer.run(max_messages=1)

    kafka_consumer.commit.assert_not_called()
