from __future__ import annotations
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol
from urllib.request import Request, urlopen
from html.parser import HTMLParser
from zoneinfo import ZoneInfo
from psycopg import Connection
from psycopg.types.json import Jsonb
from src.infrastructure.postgres.exchange_rate_provider import (
    RATE_TYPE_SELL,
    USD_TO_VND,
)


@dataclass(frozen=True, slots=True)
class ExchangeRateSnapshot:
    base_currency: str
    quote_currency: str
    rate: Decimal
    rate_at: datetime
    source: str
    source_url: str | None = None
    raw_payload: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if (self.base_currency, self.quote_currency) != USD_TO_VND:
            raise ValueError("only USD/VND snapshots are supported")
        if self.rate <= 0:
            raise ValueError("rate must be positive")
        if self.rate_at.tzinfo is None or self.rate_at.utcoffset() is None:
            raise ValueError("rate_at must be timezone-aware")
        if not self.source.strip():
            raise ValueError("source must not be blank")


class ExchangeRateFetcher(Protocol):
    def fetch_usd_vnd_sell(self) -> ExchangeRateSnapshot:
        ...


class JsonExchangeRateFetcher:
    """Fetch a configured JSON endpoint containing a USD sell rate.

    Expected response shape:
    {"USD": {"sell": 25450, "rate_at": "..."}}
    """

    def __init__(
        self,
        *,
        url: str,
        source: str,
        timeout_seconds: float = 10.0,
        http_get: Callable[[str, float], bytes] | None = None,
    ) -> None:
        if not url.strip() or not source.strip():
            raise ValueError("url and source must not be blank")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._url = url
        self._source = source
        self._timeout_seconds = timeout_seconds
        self._http_get = http_get or self._default_http_get

    @staticmethod
    def _default_http_get(url: str, timeout_seconds: float) -> bytes:
        request = Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "re-price-monitor/1"},
        )
        with urlopen(request, timeout=timeout_seconds) as response:
            if response.status < 200 or response.status >= 300:
                raise RuntimeError(f"exchange-rate HTTP status: {response.status}")
            return response.read()

    def fetch_usd_vnd_sell(self) -> ExchangeRateSnapshot:
        try:
            payload = json.loads(
                self._http_get(self._url, self._timeout_seconds).decode("utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError, OSError) as exc:
            raise RuntimeError("exchange-rate response is not valid JSON") from exc

        try:
            usd = payload["USD"]
            rate = Decimal(str(usd["sell"]))
        except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
            raise ValueError(
                "exchange-rate JSON must contain USD.sell"
            ) from exc

        rate_at_value = usd.get("rate_at")
        rate_at = (
            datetime.fromisoformat(str(rate_at_value).replace("Z", "+00:00"))
            if rate_at_value
            else datetime.now(timezone.utc)
        )
        return ExchangeRateSnapshot(
            base_currency="USD",
            quote_currency="VND",
            rate=rate,
            rate_at=rate_at,
            source=self._source,
            source_url=self._url,
            raw_payload=payload,
        )


class _RateTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_cell = False
        self._cell: list[str] = []
        self._row: list[str] = []
        self.rows: list[list[str]] = []
        self.usd_sell_rate: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if (
            tag == "li"
            and attributes.get("data-code", "").upper() == "USD"
        ):
            self.usd_sell_rate = attributes.get("data-sell-rate")
        if tag in {"td", "th"}:
            self._in_cell = True
            self._cell = []
        elif tag == "tr":
            self._row = []

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._in_cell:
            self._row.append(" ".join("".join(self._cell).split()))
            self._in_cell = False
        elif tag == "tr" and self._row:
            self.rows.append(self._row)


class VietcombankHtmlExchangeRateFetcher:
    """Fetch USD sell rate from Vietcombank's official rate page."""

    def __init__(
        self,
        *,
        url: str,
        source: str = "vietcombank.com.vn",
        timeout_seconds: float = 10.0,
        http_get: Callable[[str, float], bytes] | None = None,
    ) -> None:
        if not url.strip() or not source.strip():
            raise ValueError("url and source must not be blank")
        self._url = url
        self._source = source
        self._timeout_seconds = timeout_seconds
        self._http_get = http_get or JsonExchangeRateFetcher._default_http_get

    def fetch_usd_vnd_sell(self) -> ExchangeRateSnapshot:
        try:
            html = self._http_get(self._url, self._timeout_seconds).decode("utf-8")
        except (UnicodeDecodeError, OSError) as exc:
            raise RuntimeError("Vietcombank response could not be decoded") from exc

        parser = _RateTableParser()
        parser.feed(html)
        rate_at = self._parse_updated_at(html)
        if parser.usd_sell_rate:
            try:
                rate = Decimal(parser.usd_sell_rate)
            except InvalidOperation as exc:
                raise ValueError(
                    "Vietcombank USD data-sell-rate is invalid"
                ) from exc
            return ExchangeRateSnapshot(
                base_currency="USD",
                quote_currency="VND",
                rate=rate,
                rate_at=rate_at,
                source=self._source,
                source_url=self._url,
                raw_payload={"html": html},
            )

        sell_index: int | None = None
        data_rows: list[list[str]] = []
        for index, row in enumerate(parser.rows):
            normalized = [cell.casefold() for cell in row]
            candidate = next(
                (
                    position
                    for position, cell in enumerate(normalized)
                    if cell in {"sell", "bán", "ban"}
                ),
                None,
            )
            if candidate is not None:
                sell_index = candidate
                data_rows = parser.rows[index + 1 :]
                break

        if sell_index is None:
            raise ValueError(
                "Vietcombank HTML did not contain a sell-rate column"
            )

        for row in data_rows:
            normalized = [cell.casefold() for cell in row]
            if not any(re.fullmatch(r"usd(?:\s*-\s*.*)?", cell) for cell in normalized):
                continue
            if sell_index is not None and sell_index < len(row):
                raw_rate = row[sell_index].replace(",", "").replace(".", "")
                if raw_rate.isdigit():
                    return ExchangeRateSnapshot(
                        base_currency="USD",
                        quote_currency="VND",
                        rate=Decimal(raw_rate),
                        rate_at=rate_at,
                        source=self._source,
                        source_url=self._url,
                        raw_payload={"html": html},
                    )
        raise ValueError(
            "Vietcombank HTML did not contain a USD sell-rate table row"
        )

    @staticmethod
    def _parse_updated_at(html: str) -> datetime:
        match = re.search(
            r"(?:at|lúc)\s*(\d{1,2}):(\d{2})\s+on\s+"
            r"(\d{1,2})/(\d{1,2})/(\d{4})",
            html,
            flags=re.IGNORECASE,
        )
        if match is None:
            return datetime.now(timezone.utc)
        hour, minute, day, month, year = (
            int(value) for value in match.groups()
        )
        return datetime(
            year,
            month,
            day,
            hour,
            minute,
            tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"),
        ).astimezone(timezone.utc)


class PostgresExchangeRateUpdater:
    """Persist validated USD/VND sell-rate snapshots idempotently."""

    def __init__(
        self,
        connection: Connection[Any],
        fetcher: ExchangeRateFetcher,
    ) -> None:
        self._connection = connection
        self._fetcher = fetcher

    def run_once(self) -> ExchangeRateSnapshot:
        snapshot = self._fetcher.fetch_usd_vnd_sell()
        with self._connection.transaction():
            self._connection.execute(
                """
                INSERT INTO exchange_rates (
                    base_currency, quote_currency, rate, rate_at,
                    rate_type, source, fetched_at, source_url, raw_payload
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (
                    base_currency, quote_currency, rate_at, rate_type
                ) DO UPDATE SET
                    rate = EXCLUDED.rate,
                    fetched_at = EXCLUDED.fetched_at,
                    source = EXCLUDED.source,
                    source_url = EXCLUDED.source_url,
                    raw_payload = EXCLUDED.raw_payload
                """,
                (
                    snapshot.base_currency,
                    snapshot.quote_currency,
                    snapshot.rate,
                    snapshot.rate_at.astimezone(timezone.utc),
                    RATE_TYPE_SELL,
                    snapshot.source,
                    datetime.now(timezone.utc),
                    snapshot.source_url,
                    Jsonb(snapshot.raw_payload) if snapshot.raw_payload is not None else None,
                ),
            )
        return snapshot
