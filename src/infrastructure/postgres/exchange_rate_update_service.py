from __future__ import annotations

from psycopg import connect

from src.infrastructure.config.settings import load_settings
from src.infrastructure.postgres.exchange_rate_updater import (
    ExchangeRateSnapshot,
    JsonExchangeRateFetcher,
    PostgresExchangeRateUpdater,
    VietcombankHtmlExchangeRateFetcher,
)


def update_exchange_rate() -> ExchangeRateSnapshot:
    """Fetch and persist the configured USD/VND sell-rate snapshot."""
    settings = load_settings()
    if not settings.FX_RATE_URL or not settings.FX_RATE_SOURCE:
        raise RuntimeError(
            "FX_RATE_URL and FX_RATE_SOURCE must be configured "
            "before updating exchange rates"
        )

    fetcher_type = (
        VietcombankHtmlExchangeRateFetcher
        if settings.FX_RATE_FORMAT == "vietcombank_html"
        else JsonExchangeRateFetcher
    )
    fetcher = fetcher_type(
        url=settings.FX_RATE_URL,
        source=settings.FX_RATE_SOURCE,
        timeout_seconds=settings.FX_RATE_TIMEOUT_SECONDS,
    )
    with connect(settings.postgres_dsn) as connection:
        return PostgresExchangeRateUpdater(connection, fetcher).run_once()


if __name__ == "__main__":
    snapshot = update_exchange_rate()
    print(
        f"{snapshot.base_currency}/{snapshot.quote_currency} "
        f"sell={snapshot.rate} at={snapshot.rate_at.isoformat()} "
        f"source={snapshot.source}"
    )
