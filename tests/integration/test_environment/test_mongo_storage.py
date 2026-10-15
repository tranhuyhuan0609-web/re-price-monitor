from tests.integration.test_environment.helpers import (
    mongo_collection,
    new_event,
    store_raw_in_mongo,
)
def test_mongo_storage():
    event = new_event()
    store_raw_in_mongo(event)
    client, collection = mongo_collection()
    try:
        stored = collection.find_one({"_id": event["event_id"]})
        assert stored is not None
        assert stored["event_id"] == event["event_id"]
        assert stored["price_raw"] == event["price_raw"]
    finally:
        client.close()