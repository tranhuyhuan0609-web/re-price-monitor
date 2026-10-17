
import psycopg
import pytest

from src.infrastructure.database.postgres_config_repository import (
    PostgresConfigRepository,
)


@pytest.mark.parametrize(
    "timeout",
    [
        True,
        False,
        0,
        -1,
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_invalid_query_timeout_is_rejected(timeout):
    with pytest.raises(ValueError):
        PostgresConfigRepository(
            pool=object(),
            query_timeout=timeout,
        )


def test_valid_query_timeout_is_accepted():
    repo = PostgresConfigRepository(
        pool=object(),
        query_timeout=1.25,
    )

    assert repo._timeout_ms == "1250"


async def test_query_timeout_is_applied_to_postgres(db_pool):
    repo = PostgresConfigRepository(
        pool=db_pool,
        query_timeout=0.05,
    )

    with pytest.raises(psycopg.errors.QueryCanceled):
        async with repo._cursor() as cur:
            await cur.execute(
                "SELECT pg_sleep(0.2)"
            )
