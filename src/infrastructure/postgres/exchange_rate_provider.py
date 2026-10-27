from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Protocol
from psycopg import Connection

USD_TO_VND = ("USD", "VND")
RATE_TYPE_SELL = "sell"


class ExchangeRateProvider(Protocol):
    def get_rate(
        self,
        *,
        base_currency: str,
        quote_currency: str,
        at: datetime,
    ) -> tuple[Decimal, datetime]:
        ...


class PostgresExchangeRateProvider:
    """Read the latest rate not newer than the observation timestamp."""

    def __init__(self, connection: Connection[Any]) -> None:
        self._connection = connection

    def get_rate(
        self,
        *,
        base_currency: str,
        quote_currency: str,
        at: datetime,
    ) -> tuple[Decimal, datetime]:
        row = self._connection.execute(
            """
            SELECT rate, rate_at
            FROM exchange_rates
            WHERE base_currency = %s
              AND quote_currency = %s
              AND rate_type = %s
              AND rate_at <= %s
            ORDER BY rate_at DESC
            LIMIT 1
            """,
            (base_currency, quote_currency, RATE_TYPE_SELL, at),
        ).fetchone()
        if row is None:
            raise ValueError(
                f"no exchange rate for {base_currency}/{quote_currency} "
                f"at or before {at.isoformat()}"
            )
        return Decimal(str(row[0])), row[1].astimezone(timezone.utc)
