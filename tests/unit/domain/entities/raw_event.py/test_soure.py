from src.domain.entities.raw_event import RawEvent
def test_source_clean(raw_event):
    raw_event["source"] = "  example.com  "
    raw_event = RawEvent(**raw_event)
    assert raw_event.source == "example.com"