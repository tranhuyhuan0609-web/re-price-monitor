from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.infrastructure.postgres.exchange_rate_provider import (
    FixedExchangeRateProvider,
    PostgresExchangeRateProvider,
)


def test_postgres_provider_selects_sell_rate_before_observation_time():
    connection = MagicMock()
    connection.execute.return_value.fetchone.return_value = (
        Decimal("25450"),
        datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    rate, rate_at = PostgresExchangeRateProvider(connection).get_rate(
        base_currency="USD",
        quote_currency="VND",
        at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    assert rate == Decimal("25450")
    assert rate_at == datetime(2026, 1, 1, tzinfo=timezone.utc)
    query, params = connection.execute.call_args.args
    assert "rate_type = %s" in query
    assert params[2] == "sell"


def test_postgres_provider_fails_when_historical_rate_is_missing():
    connection = MagicMock()
    connection.execute.return_value.fetchone.return_value = None

    with pytest.raises(ValueError, match="no exchange rate"):
        PostgresExchangeRateProvider(connection).get_rate(
            base_currency="USD",
            quote_currency="VND",
            at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )


def test_fixed_provider_rejects_unsupported_pair():
    provider = FixedExchangeRateProvider(
        Decimal("25450"),
        datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    with pytest.raises(ValueError, match="unsupported exchange pair"):
        provider.get_rate(
            base_currency="EUR",
            quote_currency="VND",
            at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
