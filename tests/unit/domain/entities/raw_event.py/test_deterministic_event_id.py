
from src.domain.entities.raw_event import deterministic_event_id
def test_deterministic_event_id_returns_same_id_for_same_inputs():
    source = "example"
    url = "https://example.com/listing/123"
    crawl_run_id = "run-001"
    first_id = deterministic_event_id(
        source=source,
        url=url,
        crawl_run_id=crawl_run_id,
    )
    second_id = deterministic_event_id(
        source=source,
        url=url,
        crawl_run_id=crawl_run_id,
    )
    assert first_id == second_id
def test_deterministic_event_id_returns_different_ids_for_different_inputs():
    source = "example"
    url = "https://example.com/listing/123"
    crawl_run_id_1 = "run-001"
    crawl_run_id_2 = "run-002"
    first_id = deterministic_event_id(
        source=source,
        url=url,
        crawl_run_id=crawl_run_id_1,
    )
    second_id = deterministic_event_id(
        source=source,
        url=url,
        crawl_run_id=crawl_run_id_2,
    )
    assert first_id != second_id
