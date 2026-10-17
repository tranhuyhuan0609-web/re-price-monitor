from src.infrastructure.database.postgres_config_repository import (
    PostgresConfigRepository,
)
import asyncio
import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from _pytest.config import Config
from _pytest.nodes import Item

from src.domain.entities.crawler_config import CrawlerConfig


from dotenv import load_dotenv


def pytest_asyncio_loop_factories(
    config: Config,
    item: Item,
) -> dict[str, object] | None:
    """Use the event loop required by psycopg async connections on Windows."""
    if os.name == "nt":
        return {"windows_selector": asyncio.SelectorEventLoop}
    return None


load_dotenv()  # Load environment variables from .env file
@pytest.fixture(scope="session")
def test_database_url() -> str:
    """
    Read the connection string for the dedicated test database.

    Example:
    postgresql://user:password@localhost:5432/realestate_test
    """
    url = os.environ.get("TEST_DB_CONNINFO")

    if not url:
        pytest.fail(
            "TEST_DATABASE_URL is not set. "
            "Configure a dedicated PostgreSQL test database."
        )

    return url


@pytest_asyncio.fixture
async def db_pool(
    test_database_url: str,
) -> AsyncIterator[AsyncConnectionPool]:
    """Create and close a PostgreSQL connection pool for a test."""
    pool = AsyncConnectionPool(
        conninfo=test_database_url,
        min_size=1,
        max_size=3,
        open=False,
    )

    await pool.open()

    try:
        await pool.wait()
        yield pool
    finally:
        await pool.close()


@pytest_asyncio.fixture
async def db_connection(
    db_pool: AsyncConnectionPool,
) -> AsyncIterator[AsyncConnection]:
    """
    Provide a connection and roll back test changes afterward.

    This fixture is useful for direct database setup and assertions.
    """
    async with db_pool.connection() as conn:
        try:
            yield conn
        finally:
            await conn.rollback()


@pytest_asyncio.fixture
async def clean_crawler_configs(
    db_pool: AsyncConnectionPool,
) -> AsyncIterator[None]:
    """Remove crawler_configs rows before and after a test."""
    async with db_pool.connection() as conn:
        async with conn.transaction():
            await conn.execute("DELETE FROM crawler_configs")

    try:
        yield
    finally:
        async with db_pool.connection() as conn:
            async with conn.transaction():
                await conn.execute("DELETE FROM crawler_configs")


@pytest.fixture
def valid_config() -> CrawlerConfig:
    """Build a valid crawler configuration for tests."""
    return CrawlerConfig.model_validate(
        {"site_id": "batdongsan",
                "name": "Bat Dong San",
                "enabled": True,
                "base_url": "https://example.com",
                "start_urls": [
                    "https://example.com/buy",
                ],
                "allowed_domains": [
                    "example.com",
                ],
                "selectors": {
                    "item": ".listing",
                    "url": "a.detail-link::attr(href)",
                    "title": "a.detail-link::text",
                    
                },
                "pagination": {
                    "enabled": True,
                    "next_page": "a.next::attr(href)",
                    "max_pages": 3,
                },
                "crawler_settings": {
                    "delay": 1.0,
                    "randomize_delay": True,
                    "concurrent_requests": 4,
                    "download_timeout": 30.0,
                    "retry_enabled": True,
                    "max_retries": 3,
            },
        }
    )


@pytest.fixture
def disabled_config(
    valid_config: CrawlerConfig,
) -> CrawlerConfig:
    """Build a valid but disabled crawler configuration."""
    return valid_config.model_copy(
        update={
            "site_id": "disabled-site",
            "name": "Disabled crawler",
            "enabled": False,
        }
    )


@pytest.fixture
def another_valid_config(
    valid_config: CrawlerConfig,
) -> CrawlerConfig:
    """Build another valid configuration with a different site_id."""
    return valid_config.model_copy(
        update={
            "site_id": "another-site",
            "name": "Another crawler",
        }
    )
@pytest.fixture
def repository(
    db_pool: AsyncConnectionPool,
    clean_crawler_configs: None,
) -> "PostgresConfigRepository":
    """Provide a PostgresConfigRepository instance for tests."""

    return PostgresConfigRepository(
        pool=db_pool,
        table_name="crawler_configs",
        query_timeout=5.0,
    )