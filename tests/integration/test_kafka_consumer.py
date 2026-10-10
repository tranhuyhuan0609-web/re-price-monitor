from tests.integration.helpers import (
    make_consumer,
    new_event,
    publish_event,
    wait_for_event,
)
def test_consumer_receives_event():
    event = new_event()
    publish_event(event)
    consumer = make_consumer(f"consumer-test-{event['event_id']}")
    try:
        received_event, _ = wait_for_event(consumer, event["event_id"])
        assert received_event == event
    finally:
        consumer.close()

   