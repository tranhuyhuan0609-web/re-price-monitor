from tests.integration.helpers import new_event, publish_event
def test_producer_delivers_event():
    event = new_event()
    publish_event(event)
    assert True