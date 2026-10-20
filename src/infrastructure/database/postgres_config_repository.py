from contextlib import asynccontextmanager
import math
from typing import TYPE_CHECKING, Any, AsyncIterator
from pydantic import ValidationError
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from src.application.exceptions.config_exceptions import (
    ConfigAlreadyExistsError,
    ConfigNotFoundError,
)
from src.application.interfaces.config_repository import ConfigRepository
from src.domain.entities.crawler_config import CrawlerConfig


if TYPE_CHECKING:
    from psycopg import AsyncCursor
    from psycopg_pool import AsyncConnectionPool


class ConfigCorruptedError(ValueError):
    """Stored crawler configuration is invalid or inconsistent."""


_MIRRORED_COLUMNS = ("site_id", "name", "enabled")


class PostgresConfigRepository(ConfigRepository):
    """Async PostgreSQL repository for crawler configurations."""

    def __init__(
        self,
        pool: "AsyncConnectionPool",
        table_name: str = "crawler_configs",
        query_timeout: float = 5.0,
        schema: str | None = None,
    ) -> None:
        if pool is None:
            raise ValueError("Pool cannot be None.")

        if not isinstance(table_name, str) or not table_name.strip():
            raise ValueError("Table name must be a non-empty string.")

        if schema is not None and (
            not isinstance(schema, str) or not schema.strip()
        ):
            raise ValueError("Schema must be a non-empty string or None.")

        if (
            isinstance(query_timeout, bool)
            or not isinstance(query_timeout, (int, float))
            or not math.isfinite(query_timeout)
            or query_timeout <= 0
        ):
            raise ValueError(
                "Query timeout must be a finite positive number."
            )

        self._pool = pool
        self._query_timeout = float(query_timeout)
        self._timeout_ms = str(
            max(1, math.ceil(self._query_timeout * 1000))
        )

        table_parts = []
        if schema is not None:
            table_parts.append(schema.strip())
        table_parts.append(table_name.strip())

        table = sql.Identifier(*table_parts)

        self._q_get = sql.SQL(
            """
            SELECT site_id, name, enabled, config_json
            FROM {}
            WHERE site_id = %s
            """
        ).format(table)

        self._q_get_enabled = sql.SQL(
            """
            SELECT site_id, name, enabled, config_json
            FROM {}
            WHERE enabled = TRUE
            ORDER BY site_id
            """
        ).format(table)

        self._q_insert = sql.SQL(
            """
            INSERT INTO {} (site_id, name, enabled, config_json)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (site_id) DO NOTHING
            """
        ).format(table)

        self._q_update = sql.SQL(
            """
            UPDATE {}
            SET
                name = %s,
                enabled = %s,
                config_json = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE site_id = %s
            """
        ).format(table)

        self._q_delete = sql.SQL(
            """
            DELETE FROM {}
            WHERE site_id = %s
            """
        ).format(table)

    @asynccontextmanager
    async def _cursor(
        self,
    ) -> AsyncIterator["AsyncCursor[dict[str, Any]]"]:
        async with self._pool.connection() as conn:
            async with conn.transaction():
                await conn.execute(
                    "SELECT set_config('statement_timeout', %s, true)",
                    (self._timeout_ms,),
                )

                async with conn.cursor(row_factory=dict_row) as cur:
                    yield cur

    @staticmethod
    def _config_to_jsonb(config: CrawlerConfig) -> Jsonb:
        return Jsonb(config.model_dump(mode="json"))

    @staticmethod
    def _row_to_config(row: dict[str, Any]) -> CrawlerConfig:
        site_id = row["site_id"]
        data = row["config_json"]

        if not isinstance(data, dict):
            raise ConfigCorruptedError(
                f"config_json must be an object for site_id '{site_id}'."
            )

        for column in _MIRRORED_COLUMNS:
            if data.get(column) != row[column]:
                raise ConfigCorruptedError(
                    f"Column '{column}' does not match config_json "
                    f"for site_id '{site_id}'."
                )

        try:
            return CrawlerConfig.model_validate(data)
        except ValidationError as exc:
            raise ConfigCorruptedError(
                f"Invalid stored crawler configuration for "
                f"site_id '{site_id}'."
            ) from exc

    @staticmethod
    def _check_config(config: CrawlerConfig) -> None:
        if not isinstance(config, CrawlerConfig):
            raise TypeError("config must be a CrawlerConfig instance.")

    @staticmethod
    def _not_found(site_id: str) -> ConfigNotFoundError:
        return ConfigNotFoundError(
            f"Config with site_id '{site_id}' not found."
        )

    async def get_config(self, site_id: str) -> CrawlerConfig:
        async with self._cursor() as cur:
            await cur.execute(self._q_get, (site_id,))
            row = await cur.fetchone()

        if row is None:
            raise self._not_found(site_id)

        return self._row_to_config(row)

    async def get_enabled_configs(self) -> list[CrawlerConfig]:
        async with self._cursor() as cur:
            await cur.execute(self._q_get_enabled)
            rows = await cur.fetchall()

        return [self._row_to_config(row) for row in rows]

    async def create_config(self, config: CrawlerConfig) -> None:
        self._check_config(config)

        async with self._cursor() as cur:
            await cur.execute(
                self._q_insert,
                (
                    config.site_id,
                    config.name,
                    config.enabled,
                    self._config_to_jsonb(config),
                ),
            )

            inserted = cur.rowcount

        if inserted == 0:
            raise ConfigAlreadyExistsError(
                f"Config with site_id '{config.site_id}' already exists."
            )

    async def update_config(
        self,
        site_id: str,
        config: CrawlerConfig,
    ) -> None:
        self._check_config(config)

        if config.site_id != site_id:
            raise ValueError(
                "Config site_id does not match the requested site_id."
            )

        async with self._cursor() as cur:
            await cur.execute(
                self._q_update,
                (
                    config.name,
                    config.enabled,
                    self._config_to_jsonb(config),
                    site_id,
                ),
            )

            updated = cur.rowcount

        if updated == 0:
            raise self._not_found(site_id)

    async def delete_config(self, site_id: str) -> None:
        async with self._cursor() as cur:
            await cur.execute(self._q_delete, (site_id,))
            deleted = cur.rowcount

        if deleted == 0:
            raise self._not_found(site_id)
