from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.infrastructure.postgres.exchange_rate_updater import (
    JsonExchangeRateFetcher,
)


def test_json_fetcher_parses_usd_sell_rate():
    fetcher = JsonExchangeRateFetcher(
        url="https://rates.example.test/latest",
        source="rates.example.test",
        http_get=lambda url, timeout: (
            b'{"USD":{"sell":"25450","rate_at":"2026-01-01T00:00:00Z"}}'
        ),
    )

    snapshot = fetcher.fetch_usd_vnd_sell()

    assert snapshot.rate == Decimal("25450")
    assert snapshot.rate_at == datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert snapshot.source_url == "https://rates.example.test/latest"


def test_json_fetcher_rejects_missing_usd_sell_rate():
    fetcher = JsonExchangeRateFetcher(
        url="https://rates.example.test/latest",
        source="rates.example.test",
        http_get=lambda url, timeout: b'{"EUR":{"sell":"28000"}}',
    )

    with pytest.raises(ValueError, match="USD.sell"):
        fetcher.fetch_usd_vnd_sell()
