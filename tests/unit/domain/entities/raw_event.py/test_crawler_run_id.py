from src.domain.entities.raw_event import RawEvent
import pytest
def test_crawl_run_id_clean(raw_event):
    raw_event["crawl_run_id"] = "  run-001  "
    raw_event = RawEvent(**raw_event)
    assert raw_event.crawl_run_id == "run-001"
def test_crawl_run_id_empty_raises_error(raw_event):
    raw_event["crawl_run_id"] = "  "
    with pytest.raises(ValueError):
        RawEvent(**raw_event)