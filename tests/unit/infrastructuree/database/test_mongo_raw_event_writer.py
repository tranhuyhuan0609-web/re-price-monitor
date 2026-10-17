from unittest.mock import MagicMock, Mock

from src.infrastructure.database.mongo_raw_event_writer import MongoRawEventWriter


def _envelope() -> bytes:
    return (
        b'{"crawl_run_id":"run-1","crawled_at":"2026-01-01T00:00:00Z",'
        b'"event_type":"listing.raw","listing_key":"batdongsan:123",'
        b'"parser_version":"v1","payload":{"url":"https://example.com/123"},'
        b'"raw_event_id":"event-1","schema_version":1,"source":"batdongsan"}'
    )


def test_writer_upserts_by_raw_event_id():
    collection = Mock()
    collection.create_index = Mock()
    client = MagicMock()
    client.__getitem__.return_value.__getitem__.return_value = collection
    message = Mock()
    message.value.return_value = _envelope()
    message.topic.return_value = "realestate.raw.v1"
    message.partition.return_value = 1
    message.offset.return_value = 7

    writer = MongoRawEventWriter(
        mongo_uri="mongodb://localhost:27017",
        database="realestate",
        client=client,
    )
    writer.handle(message)

    collection.replace_one.assert_called_once()
    filter_value, document = collection.replace_one.call_args.args[:2]
    assert filter_value == {"_id": "event-1"}
    assert document["_id"] == "event-1"
    assert document["listing_key"] == "batdongsan:123"
    assert document["kafka"]["offset"] == 7
