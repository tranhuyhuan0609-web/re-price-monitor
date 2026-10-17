
import pytest

from src.infrastructure.crawler import scrapy_worker
def test_close_timeout_returns_default_when_not_set():
    payload = {}

    result = scrapy_worker._optional_positive_int(
        payload,
        "closespider_timeout",
        scrapy_worker.DEFAULT_CLOSESPIDER_TIMEOUT,
    )

    assert result == scrapy_worker.DEFAULT_CLOSESPIDER_TIMEOUT


def test_close_timeout_rejects_bool():
    payload = {"closespider_timeout": True}

    with pytest.raises(
        ValueError,
        match="closespider_timeout must be a positive integer",
    ):
        scrapy_worker._optional_positive_int(
            payload,
            "closespider_timeout",
            scrapy_worker.DEFAULT_CLOSESPIDER_TIMEOUT,
        )

def test_close_timeout_rejects_negative_integer():
    payload = {"closespider_timeout": -10}

    with pytest.raises(
        ValueError,
        match="closespider_timeout must be a positive integer",
    ):
        scrapy_worker._optional_positive_int(
            payload,
            "closespider_timeout",
            scrapy_worker.DEFAULT_CLOSESPIDER_TIMEOUT,
        )
def test_close_timeout_rejects_string():
    payload = {"closespider_timeout": "not-an-integer"}

    with pytest.raises(
        ValueError,
        match="closespider_timeout must be a positive integer",
    ):
        scrapy_worker._optional_positive_int(
            payload,
            "closespider_timeout",
            scrapy_worker.DEFAULT_CLOSESPIDER_TIMEOUT,
        )
