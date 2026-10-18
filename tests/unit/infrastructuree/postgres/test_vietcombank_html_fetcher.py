from datetime import datetime, timezone
from decimal import Decimal

from src.infrastructure.postgres.exchange_rate_updater import (
    VietcombankHtmlExchangeRateFetcher,
)


def test_vietcombank_html_fetcher_reads_usd_sell_rate():
    html = b"""
    <table>
      <tr><th>Currency</th><th>Buy</th><th>Transfer</th><th>Sell</th></tr>
      <tr><td>USD</td><td>25,800</td><td>25,850</td><td>26,080</td></tr>
    </table>
    """
    fetcher = VietcombankHtmlExchangeRateFetcher(
        url="https://www.vietcombank.com.vn/en/Personal/Cong-cu-Tien-ich/Ty-gia",
        http_get=lambda url, timeout: html,
    )

    snapshot = fetcher.fetch_usd_vnd_sell()

    assert snapshot.rate == Decimal("26080")
    assert snapshot.source == "vietcombank.com.vn"
    assert snapshot.raw_payload == {"html": html.decode()}


def test_vietcombank_html_fetcher_reads_official_data_attribute():
    html = (
        b'<span>Exchange rate updated at 23:00 on 16/10/2026</span>'
        b'<li class="dropdown-options__item" data-code="USD" '
        b'data-sell-rate="26080.00"></li>'
    )
    fetcher = VietcombankHtmlExchangeRateFetcher(
        url="https://www.vietcombank.com.vn/en/Personal/Cong-cu-Tien-ich/Ty-gia",
        http_get=lambda url, timeout: html,
    )

    snapshot = fetcher.fetch_usd_vnd_sell()
    assert snapshot.rate == Decimal("26080.00")
    assert snapshot.rate_at == datetime(
        2026, 10, 16, 16, 0, tzinfo=timezone.utc
    )


def test_vietcombank_html_fetcher_rejects_missing_usd_row():
    fetcher = VietcombankHtmlExchangeRateFetcher(
        url="https://rates.example.test",
        http_get=lambda url, timeout: (
            b"<table><tr><th>Sell</th></tr><tr><td>EUR</td></tr></table>"
        ),
    )

    import pytest

    with pytest.raises(ValueError, match="USD sell-rate"):
        fetcher.fetch_usd_vnd_sell()
