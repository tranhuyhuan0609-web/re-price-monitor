
import pytest

from src.domain.entities.raw_event import RawEvent, RawEventBuildError
def test_payload_rejects_list(raw_event):
    raw_event["raw_payload"] = ["listing", "price", 100]
    with pytest.raises(RawEventBuildError):
        RawEvent(**raw_event)
def test_pay_load_with_dict(raw_event):
    raw_event["raw_payload"] = {"listing": {"price": 100}}
    event = RawEvent(**raw_event)
    assert event.raw_payload == {"listing": {"price": 100}}
