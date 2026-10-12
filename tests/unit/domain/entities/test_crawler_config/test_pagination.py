
from pydantic import ValidationError
import pytest

from src.domain.entities.crawler_config import Pagination


def test_pagination_defaults():
    pagination = Pagination()

    assert pagination.enabled is False
    assert pagination.next_page is None
    assert pagination.max_pages == 100


def test_pagination_enabled_with_next_page():
    pagination = Pagination(
        enabled=True,
        next_page="a.next::attr(href)",
        max_pages=10,
    )

    assert pagination.enabled is True
    assert pagination.next_page == "a.next::attr(href)"
    assert pagination.max_pages == 10


def test_pagination_enabled_without_next_page():
    with pytest.raises(ValidationError):
        Pagination(
            enabled=True,
            next_page=None,
        )


def test_pagination_disabled_with_next_page():
    with pytest.raises(ValidationError):
        Pagination(
            enabled=False,
            next_page="a.next::attr(href)",
        )


def test_pagination_max_pages_must_be_positive():
    with pytest.raises(ValidationError):
        Pagination(
            enabled=False,
            max_pages=0,
        )