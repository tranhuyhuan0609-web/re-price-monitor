from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.infrastructure.postgres.exchange_rate_updater import (
    ExchangeRateSnapshot,
    PostgresExchangeRateUpdater,
)


def _snapshot() -> ExchangeRateSnapshot:
    return ExchangeRateSnapshot(
        base_currency="USD",
        quote_currency="VND",
        rate=Decimal("25450"),
        rate_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        source="bank.example",
        source_url="https://bank.example/rates",
        raw_payload={"usd_sell": "25450"},
    )


def test_updater_persists_sell_rate_snapshot():
    connection = MagicMock()
    fetcher = MagicMock()
    fetcher.fetch_usd_vnd_sell.return_value = _snapshot()

    result = PostgresExchangeRateUpdater(connection, fetcher).run_once()

    assert result.rate == Decimal("25450")
    query, params = connection.execute.call_args.args
    assert "ON CONFLICT" in query
    assert params[4] == "sell"
    assert params[5] == "bank.example"


def test_snapshot_rejects_naive_timestamp():
    with pytest.raises(ValueError, match="timezone-aware"):
        ExchangeRateSnapshot(
            base_currency="USD",
            quote_currency="VND",
            rate=Decimal("25450"),
            rate_at=datetime(2026, 1, 1),
            source="bank.example",
        )
