from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from src.infrastructure.postgres.exchange_rate_update_service import (
    update_exchange_rate,
)


def test_update_exchange_rate_requires_source_configuration():
    settings = Mock(FX_RATE_URL=None, FX_RATE_SOURCE=None)
    with patch(
        "src.infrastructure.postgres.exchange_rate_update_service.load_settings",
        return_value=settings,
    ):
        with pytest.raises(RuntimeError, match="FX_RATE_URL"):
            update_exchange_rate()


def test_update_exchange_rate_wires_fetcher_and_updater():
    settings = Mock(
        FX_RATE_URL="https://rates.example.test/latest",
        FX_RATE_SOURCE="rates.example.test",
        FX_RATE_TIMEOUT_SECONDS=10,
        postgres_dsn="postgresql://test",
    )
    snapshot = Mock(rate=Decimal("25450"))
    fetcher = Mock()
    updater = Mock()
    updater.run_once.return_value = snapshot

    with (
        patch(
            "src.infrastructure.postgres.exchange_rate_update_service.load_settings",
            return_value=settings,
        ),
        patch(
            "src.infrastructure.postgres.exchange_rate_update_service.JsonExchangeRateFetcher",
            return_value=fetcher,
        ),
        patch(
            "src.infrastructure.postgres.exchange_rate_update_service.PostgresExchangeRateUpdater",
            return_value=updater,
        ),
        patch(
            "src.infrastructure.postgres.exchange_rate_update_service.connect"
        ) as connect,
    ):
        connect.return_value.__enter__.return_value = Mock()
        assert update_exchange_rate() is snapshot

    fetcher.fetch_usd_vnd_sell.assert_not_called()
    updater.run_once.assert_called_once()
