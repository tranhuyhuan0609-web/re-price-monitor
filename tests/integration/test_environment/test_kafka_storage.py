
# import uuid

# from tests.integration.test_environment.helpers import (
#     consume_and_store,
#     new_event,
#     publish_event,
#     store_clean_in_postgres,
#     store_raw_in_mongo,
# )


# def test_kafka_to_mongo_and_postgres():
#     message = new_event(
#         event_id=str(uuid.uuid4()),
#         source="smoke",
#         price_raw="3,5 tỷ",
#     )

#     # 1. Publish one event to Kafka.
#     publish_event(message)

#     # 2. RAW consumer group stores the event in MongoDB.
#     raw_event = consume_and_store(
#         group_id=f"smoke-raw-{message['event_id']}",
#         expected_id=message["event_id"],
#         store_callback=store_raw_in_mongo,
#     )

#     # 3. CLEAN consumer group independently stores the event
#     #    in PostgreSQL.
#     clean_event = consume_and_store(
#         group_id=f"smoke-clean-{message['event_id']}",
#         expected_id=message["event_id"],
#         store_callback=store_clean_in_postgres,
#     )

#     # 4. Verify both groups received the expected event.
#     assert raw_event == message
#     assert clean_event == message
