from __future__ import annotations

import json
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import psycopg
from psycopg_pool import ConnectionPool

from src.infrastructure.config.settings import load_settings


BATCH_SIZE = 1000
POOL_SIZE = 8
WORKERS = 1
MONTHS = (
    ("2026-09-01T00:00:00+00:00", "2026-10-01T00:00:00+00:00"),
    ("2026-10-01T00:00:00+00:00", "2026-11-01T00:00:00+00:00"),
    ("2026-11-01T00:00:00+00:00", "2026-12-01T00:00:00+00:00"),
)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, default=str),
        encoding="utf-8",
    )


def make_values(rows: int) -> list[tuple[str, int, float, datetime]]:
    values: list[tuple[str, int, float, datetime]] = []
    for index in range(rows):
        month = index % len(MONTHS)
        timestamp = datetime.fromisoformat(MONTHS[month][0])
        values.append(
            (
                f"partition-benchmark:{index}",
                1_000_000_000 + index,
                50 + (index % 100),
                timestamp,
            )
        )
    return values


def create_tables(connection: psycopg.Connection[Any], suffix: str) -> tuple[str, str]:
    plain = f"benchmark_plain_{suffix}"
    partitioned = f"benchmark_partitioned_{suffix}"
    connection.execute(
        f"""
        CREATE TABLE {plain} (
            listing_key TEXT NOT NULL,
            price_vnd NUMERIC(18, 0) NOT NULL,
            area_m2 NUMERIC(12, 2) NOT NULL,
            run_started_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    connection.execute(
        f"""
        CREATE TABLE {partitioned} (
            listing_key TEXT NOT NULL,
            price_vnd NUMERIC(18, 0) NOT NULL,
            area_m2 NUMERIC(12, 2) NOT NULL,
            run_started_at TIMESTAMPTZ NOT NULL
        ) PARTITION BY RANGE (run_started_at)
        """
    )
    for index, (start, end) in enumerate(MONTHS):
        connection.execute(
            f"""
            CREATE TABLE {partitioned}_{index}
            PARTITION OF {partitioned}
            FOR VALUES FROM ('{start}'::timestamptz)
                       TO ('{end}'::timestamptz)
            """
        )
    connection.commit()
    return plain, partitioned


def insert_rows(
    dsn: str,
    table: str,
    values: list[tuple[str, int, float, datetime]],
) -> dict[str, Any]:
    chunks = [
        values[index:index + BATCH_SIZE]
        for index in range(0, len(values), BATCH_SIZE)
    ]

    def insert_chunk(chunk: list[tuple[str, int, float, datetime]]) -> int:
        with pool.connection() as connection:
            with connection.transaction():
                with connection.cursor() as cursor:
                    cursor.executemany(
                        f"""
                        INSERT INTO {table}
                            (listing_key, price_vnd, area_m2, run_started_at)
                        VALUES (%s, %s, %s, %s)
                        """,
                        chunk,
                    )
        return len(chunk)

    started = time.perf_counter()
    with ConnectionPool(
        conninfo=dsn,
        min_size=POOL_SIZE,
        max_size=POOL_SIZE,
        open=True,
    ) as pool:
        with ThreadPoolExecutor(max_workers=WORKERS) as executor:
            inserted = sum(executor.map(insert_chunk, chunks))
    elapsed = time.perf_counter() - started
    return {
        "rows_inserted": inserted,
        "elapsed_seconds": round(elapsed, 6),
        "rows_per_second": round(inserted / elapsed, 2),
    }


def timed_query(
    connection: psycopg.Connection[Any],
    table: str,
    where: str,
    params: tuple[Any, ...],
) -> dict[str, Any]:
    started = time.perf_counter()
    count = connection.execute(
        f"SELECT count(*) FROM {table} WHERE {where}",
        params,
    ).fetchone()[0]
    elapsed = time.perf_counter() - started
    plan = connection.execute(
        f"""
        EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
        SELECT count(*) FROM {table} WHERE {where}
        """,
        params,
    ).fetchone()[0][0]
    return {
        "rows": count,
        "elapsed_seconds": round(elapsed, 6),
        "planning_time_ms": plan.get("Planning Time"),
        "execution_time_ms": plan.get("Execution Time"),
        "plan": plan.get("Plan"),
    }


def run(rows: int, output: Path) -> None:
    settings = load_settings()
    suffix = uuid.uuid4().hex[:12]
    values = make_values(rows)
    with psycopg.connect(settings.postgres_dsn) as connection:
        plain, partitioned = create_tables(connection, suffix)
        try:
            results: dict[str, Any] = {
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "rows": rows,
                "batch_size": BATCH_SIZE,
                "pool_size": POOL_SIZE,
                "workers": WORKERS,
                "plain": insert_rows(settings.postgres_dsn, plain, values),
                "partitioned": insert_rows(
                    settings.postgres_dsn,
                    partitioned,
                    values,
                ),
                "queries": {},
            }
            for table_name, label in (
                (plain, "plain"),
                (partitioned, "partitioned"),
            ):
                results["queries"][label] = {
                    "single_month": timed_query(
                        connection,
                        table_name,
                        "run_started_at >= %s AND run_started_at < %s",
                        MONTHS[1],
                    ),
                    "all_rows": timed_query(
                        connection,
                        table_name,
                        "listing_key LIKE %s",
                        ("partition-benchmark:%",),
                    ),
                }
            write_json(output, results)
        finally:
            connection.execute(f"DROP TABLE IF EXISTS {partitioned} CASCADE")
            connection.execute(f"DROP TABLE IF EXISTS {plain}")
            connection.commit()


if __name__ == "__main__":
    run(
        rows=100_000,
        output=ROOT / "benchmark_results_100k_partition" / "summary.json",
    )
    print("Partition benchmark complete.")
