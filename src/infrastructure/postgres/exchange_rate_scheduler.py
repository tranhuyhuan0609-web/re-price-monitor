from __future__ import annotations
import logging
import time
from collections.abc import Callable
from src.infrastructure.config.settings import load_settings
from src.infrastructure.postgres.exchange_rate_update_service import (
    update_exchange_rate,
)

logger = logging.getLogger(__name__)


class ExchangeRateScheduler:
    """Run the configured exchange-rate update at a fixed interval."""

    def __init__(
        self,
        *,
        update: Callable[[], object] = update_exchange_rate,
        interval_seconds: int = 3600,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if interval_seconds < 60:
            raise ValueError("interval_seconds must be at least 60")
        self._update = update
        self._interval_seconds = interval_seconds
        self._sleep = sleep

    def run_once(self) -> object:
        return self._update()

    def run_forever(self) -> None:
        while True:
            try:
                self.run_once()
            except Exception:
                logger.exception("Exchange-rate update failed")
            self._sleep(self._interval_seconds)


def run_exchange_rate_scheduler() -> None:
    settings = load_settings()
    ExchangeRateScheduler(
        interval_seconds=settings.FX_RATE_UPDATE_INTERVAL_SECONDS,
    ).run_forever()


if __name__ == "__main__":
    run_exchange_rate_scheduler()
