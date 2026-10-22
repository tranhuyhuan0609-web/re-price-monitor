from __future__ import annotations
import os
from src.application.parsers.text_utils import remove_emoji_and_clean
from threading import RLock
from typing import Any
import psycopg
from psycopg.rows import dict_row


class PostgresListingDetailCache:
    """Persistent cache for detail-page fields, keyed by site and listing_key.

    This is crawler operational state, not a replacement for MongoDB RAW or
    PostgreSQL CLEAN. Cached fields are reattached to every RawEvent so a list-
    only run will not erase previously captured description/contact data.
    """

    def __init__(
        self,
        *,
        conninfo: dict[str, Any],
        refresh_after_seconds: int = 7 * 24 * 60 * 60,
        retry_missing_after_seconds: int = 6 * 60 * 60,
    ) -> None:
        if refresh_after_seconds <= 0:
            raise ValueError("refresh_after_seconds must be positive")
        if retry_missing_after_seconds <= 0:
            raise ValueError("retry_missing_after_seconds must be positive")

        self._conninfo = dict(conninfo)
        self.refresh_after_seconds = refresh_after_seconds
        self.retry_missing_after_seconds = retry_missing_after_seconds
        self._connection: psycopg.Connection[Any] | None = None
        self._lock = RLock()

    @classmethod
    def from_environment(cls) -> "PostgresListingDetailCache":
        """Build cache connection details from the project's .env settings."""
        required = (
            "POSTGRES_DB",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
        )
        missing = [key for key in required if os.getenv(key) is None]
        if missing:
            raise RuntimeError(
                "Missing PostgreSQL environment variables for detail cache: "
                + ", ".join(missing)
            )

        return cls(
            conninfo={
                "host": os.getenv("POSTGRES_HOST", "localhost"),
                "port": int(os.getenv("POSTGRES_PORT", "5432")),
                "dbname": os.environ["POSTGRES_DB"],
                "user": os.environ["POSTGRES_USER"],
                "password": os.environ["POSTGRES_PASSWORD"],
                "connect_timeout": 5,
                "application_name": "realestate-detail-cache",
            },
            refresh_after_seconds=int(
                os.getenv("DETAIL_CACHE_REFRESH_SECONDS", str(7 * 24 * 60 * 60))
            ),
            retry_missing_after_seconds=int(
                os.getenv(
                    "DETAIL_CACHE_RETRY_MISSING_SECONDS",
                    str(6 * 60 * 60),
                )
            ),
        )

    def _get_connection(self) -> psycopg.Connection[Any]:
        if self._connection is None or self._connection.closed:
            self._connection = psycopg.connect(
                **self._conninfo,
                autocommit=True,
            )
        return self._connection

    def check_schema(self) -> None:
        """Fail fast if the migration was not applied."""
        with self._lock:
            connection = self._get_connection()
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT site_id, listing_key, listing_url, description,
                           contact_info, last_attempt_at, last_success_at,
                           last_outcome
                    FROM crawler_listing_detail_cache
                    LIMIT 0
                    """
                )

    def get_many(
        self,
        site_id: str,
        listing_keys: list[str],
    ) -> dict[str, dict[str, Any]]:
        """Return cached state for a batch of listings in one database query."""
        keys = list(dict.fromkeys(key for key in listing_keys if key))
        if not keys:
            return {}

        with self._lock:
            connection = self._get_connection()
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    SELECT listing_key, listing_url, description, contact_info,
                           last_attempt_at, last_success_at, last_outcome
                    FROM crawler_listing_detail_cache
                    WHERE site_id = %s AND listing_key = ANY(%s::text[])
                    """,
                    (site_id, keys),
                )
                rows = cursor.fetchall()

        return {row["listing_key"]: dict(row) for row in rows}

    def upsert(
        self,
        *,
        site_id: str,
        listing_key: str,
        listing_url: str,
        description: str | None,
        contact_info: str | None,
        fetch_succeeded: bool,
    ) -> None:
        """Persist the latest attempt, preserving known values on empty results."""
        clean_description = remove_emoji_and_clean(description) if description else None
        clean_contact = remove_emoji_and_clean(contact_info) if contact_info else None

        with self._lock:
            connection = self._get_connection()
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO crawler_listing_detail_cache (
                        site_id, listing_key, listing_url,
                        description, contact_info,
                        last_attempt_at, last_success_at,
                        last_outcome, updated_at
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, NOW(),
                        CASE WHEN %s THEN NOW() ELSE NULL END,
                        CASE WHEN %s THEN 'success' ELSE 'failed' END,
                        NOW()
                    )
                    ON CONFLICT (site_id, listing_key)
                    DO UPDATE SET
                        listing_url = EXCLUDED.listing_url,
                        description = COALESCE(
                            NULLIF(EXCLUDED.description, ''),
                            crawler_listing_detail_cache.description
                        ),
                        contact_info = COALESCE(
                            NULLIF(EXCLUDED.contact_info, ''),
                            crawler_listing_detail_cache.contact_info
                        ),
                        last_attempt_at = NOW(),
                        last_success_at = COALESCE(
                            EXCLUDED.last_success_at,
                            crawler_listing_detail_cache.last_success_at
                        ),
                        last_outcome = EXCLUDED.last_outcome,
                        updated_at = NOW()
                    """,
                    (
                        site_id,
                        listing_key,
                        listing_url,
                        clean_description,
                        clean_contact,
                        fetch_succeeded,
                        fetch_succeeded,
                    ),
                )

    def close(self) -> None:
        with self._lock:
            if self._connection is not None and not self._connection.closed:
                self._connection.close()
            self._connection = None
