
import io
import pytest
from src.infrastructure.crawler import scrapy_worker
def test_read_payload_returns_dict_when_json_is_valid(monkeypatch):
    payload = '{"crawl_run_id": "run-001"}'
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))
    result = scrapy_worker._read_payload()
    assert result == {"crawl_run_id": "run-001"}
def test_read_payload_raises_value_error_when_json_is_invalid(monkeypatch):
    payload = '{"crawl_run_id": "run-001"'
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))
    try:
        scrapy_worker._read_payload()
    except ValueError as e:
        assert str(e) == "Worker payload must be valid JSON."
def test_read_payload_raises_value_error_when_json_is_empty(monkeypatch):
    payload = ''
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))
    with pytest.raises(ValueError) as e:
        scrapy_worker._read_payload()
    assert str(e.value) == "Missing worker payload on stdin."
def test_read_payload_raises_value_error_when_json_is_not_dict(monkeypatch):
    payload = '["not", "a", "dict"]'
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))
    with pytest.raises(ValueError) as e:
        scrapy_worker._read_payload()
    assert str(e.value) == "Worker payload must be a JSON object."