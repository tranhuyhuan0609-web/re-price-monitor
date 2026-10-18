from unittest.mock import Mock

import pytest

from src.infrastructure.postgres.exchange_rate_scheduler import (
    ExchangeRateScheduler,
)


def test_exchange_rate_scheduler_runs_one_update():
    update = Mock(return_value="snapshot")
    scheduler = ExchangeRateScheduler(update=update)

    assert scheduler.run_once() == "snapshot"
    update.assert_called_once_with()


def test_exchange_rate_scheduler_rejects_too_short_interval():
    with pytest.raises(ValueError, match="at least 60"):
        ExchangeRateScheduler(interval_seconds=59)
