from __future__ import annotations
import logging
import time
from collections.abc import Callable
from typing import Any
from psycopg import Connection, connect
from src.infrastructure.config.settings import load_settings
logger = logging.getLogger(__name__)

# Advisory lock key to serialize concurrent maintainers; 
# otherwise, they might race on the same partition name.
_ADVISORY_LOCK_KEY = 7243001

def ensure_partitions(connection: Connection[Any], months_ahead: int) -> None:
    """Create the current and upcoming monthly listing_observation partitions."""
    if not 0 <= months_ahead <= 24:
        raise ValueError("months_ahead must be between 0 and 24")

    with connection.transaction():
        connection.execute(
            "SELECT pg_advisory_xact_lock(%s)", (_ADVISORY_LOCK_KEY,)
        )
        connection.execute(
            "SELECT ensure_observation_partitions(%s)", (months_ahead,)
        )

class PartitionMaintainer:
    """Keep future partitions available so inserts never hit a missing month."""

    def __init__(
        self,
        *,
        dsn: str,
        months_ahead: int = 2,
        interval_seconds: int = 21600,
        connect_fn: Callable[[str], Connection[Any]] = connect,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if interval_seconds < 60:
            raise ValueError("interval_seconds must be at least 60")
        if not 0 <= months_ahead <= 24:
            raise ValueError("months_ahead must be between 0 and 24")
        self._dsn = dsn
        self._months_ahead = months_ahead
        self._interval_seconds = interval_seconds
        self._connect = connect_fn
        self._sleep = sleep

    def run_once(self) -> None:
        # A fresh connection per run survives database restarts.
        with self._connect(self._dsn) as connection:
            ensure_partitions(connection, self._months_ahead)
        logger.info(
            "Observation partitions ensured for %d month(s) ahead",
            self._months_ahead,
        )

    def run_forever(self) -> None:
        while True:
            try:
                self.run_once()
            except Exception:
                logger.exception("Partition maintenance failed")
            self._sleep(self._interval_seconds)

def run_partition_maintenance() -> None:
    settings = load_settings()
    PartitionMaintainer(
        dsn=settings.postgres_dsn,
        months_ahead=settings.PARTITION_MONTHS_AHEAD,
        interval_seconds=settings.PARTITION_CHECK_INTERVAL_SECONDS,
    ).run_forever()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_partition_maintenance()