from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, Mock

import pytest

from src.infrastructure.postgres.raw_event_clean_processor import (
    RawEventCleanProcessor,
    parse_area_m2,
    parse_price,
    parse_price_vnd,
)
from src.infrastructure.postgres.exchange_rate_provider import (
    FixedExchangeRateProvider,
)


def test_parse_batdongsan_price_and_area():
    assert parse_price_vnd("8,48 tỷ") == Decimal("8480000000")
    assert parse_area_m2("75 m²") == Decimal("75.00")


def test_processor_writes_event_observation_and_lifecycle():
    connection = MagicMock()
    message = Mock()
    message.value.return_value = (
        b'{"event_type":"listing.raw","schema_version":1,'
        b'"raw_event_id":"event-1","crawl_run_id":"run-1",'
        b'"source":"batdongsan","listing_key":"batdongsan:123",'
        b'"parser_version":"1.0.0","crawled_at":"2026-01-01T00:00:00Z",'
        b'"payload":{"url":"https://example.com/123","title":"Ban nha",'
        b'"source_listing_id":"123","raw_price":"8,48 ty",'
        b'"raw_area":"75 m2","raw_address":"Ha Noi","quality_flags":[]}}'
    )

    RawEventCleanProcessor(connection).handle(message)

    assert connection.execute.call_count == 3
    assert connection.transaction.called
    statements = [
        call.args[0] for call in connection.execute.call_args_list
    ]
    assert "processed_raw_events" in statements[0]
    assert "listing_observation" in statements[1]
    assert "listing_lifecycle" in statements[2]


def test_parse_price_requires_value():
    with pytest.raises(ValueError, match="raw_price"):
        parse_price_vnd(None)


def test_parse_negotiable_price_as_contact():
    assert parse_price_vnd("Giá thỏa thuận") is None


def test_parse_usd_price_preserves_currency_and_amount():
    parsed = parse_price("$250,000")
    assert parsed.amount == Decimal("250000")
    assert parsed.currency == "USD"
    assert parsed.status == "known"


def test_processor_converts_usd_using_rate_provider():
    connection = MagicMock()
    message = Mock()
    message.value.return_value = (
        b'{"event_type":"listing.raw","schema_version":1,'
        b'"raw_event_id":"event-usd","crawl_run_id":"run-1",'
        b'"source":"example","listing_key":"example:1",'
        b'"parser_version":"1.0.0","crawled_at":"2026-01-01T00:00:00Z",'
        b'"payload":{"url":"https://example.com/1","title":"House",'
        b'"raw_price":"$250,000","raw_area":"100 m2","quality_flags":[]}}'
    )
    provider = FixedExchangeRateProvider(
        Decimal("25000"),
        datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    RawEventCleanProcessor(connection, provider).handle(message)

    observation_call = connection.execute.call_args_list[1]
    params = observation_call.args[1]
    assert Decimal("250000") in params
    assert Decimal("6250000000") in params
    assert Decimal("25000") in params
