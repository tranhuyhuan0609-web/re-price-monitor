from __future__ import annotations

import argparse
import json
import sys
import statistics
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import psycopg
from confluent_kafka import Consumer, Producer
from confluent_kafka.admin import AdminClient, NewTopic
from pymongo import MongoClient
from psycopg_pool import ConnectionPool

from src.infrastructure.config.settings import load_settings


DEFAULT_OUTPUT = ROOT / "benchmark_results"
BENCHMARK_TABLE = "benchmark_listing_observation"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def benchmark_postgres(
    settings: Any,
    *,
    rows: int,
    batch_size: int,
    pool_size: int,
    workers: int,
) -> dict[str, Any]:
    dsn = settings.postgres_dsn
    with psycopg.connect(dsn) as connection:
        connection.execute(f"""
            CREATE TABLE IF NOT EXISTS {BENCHMARK_TABLE} (
                id BIGSERIAL PRIMARY KEY,
                listing_key TEXT NOT NULL,
                price_vnd NUMERIC(18, 0) NOT NULL,
                area_m2 NUMERIC(12, 2) NOT NULL,
                crawled_at TIMESTAMPTZ NOT NULL
            )
        """)
        connection.commit()
        connection.execute(f"TRUNCATE {BENCHMARK_TABLE}")
        connection.commit()

    values = [
        (f"benchmark:{index}", 1000000000 + index, 50 + (index % 100))
        for index in range(rows)
    ]
    chunks = [
        values[index:index + batch_size]
        for index in range(0, len(values), batch_size)
    ]

    def insert_chunk(chunk: list[tuple[str, int, int]]) -> int:
        with pool.connection() as connection:
            with connection.transaction():
                with connection.cursor() as cursor:
                    cursor.executemany(
                    f"""
                    INSERT INTO {BENCHMARK_TABLE}
                        (listing_key, price_vnd, area_m2, crawled_at)
                    VALUES (%s, %s, %s, now())
                    """,
                    chunk,
                    )
        return len(chunk)

    started = time.perf_counter()
    with ConnectionPool(
        conninfo=dsn,
        min_size=pool_size,
        max_size=pool_size,
        open=True,
    ) as pool:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            inserted = sum(executor.map(insert_chunk, chunks))
    elapsed = time.perf_counter() - started

    with psycopg.connect(dsn) as connection:
        persisted = connection.execute(
            f"SELECT count(*) FROM {BENCHMARK_TABLE}"
        ).fetchone()[0]

    return {
        "benchmark": "postgres",
        "timestamp_utc": now_iso(),
        "rows_requested": rows,
        "rows_inserted": inserted,
        "rows_persisted": persisted,
        "batch_size": batch_size,
        "pool_size": pool_size,
        "workers": workers,
        "elapsed_seconds": round(elapsed, 6),
        "rows_per_second": round(inserted / elapsed, 2) if elapsed else 0,
        "status": "passed" if persisted == rows else "failed",
    }


def benchmark_mongo(
    settings: Any,
    *,
    rows: int,
    batch_size: int,
    pool_size: int,
    workers: int,
) -> dict[str, Any]:
    collection_name = f"benchmark_{uuid.uuid4().hex[:12]}"
    client = MongoClient(settings.mongo_uri, maxPoolSize=pool_size)
    collection = client[settings.MONGO_DB][collection_name]
    values = [
        {
            "listing_key": f"benchmark:{index}",
            "price_vnd": 1000000000 + index,
            "area_m2": 50 + (index % 100),
        }
        for index in range(rows)
    ]
    chunks = [
        values[index:index + batch_size]
        for index in range(0, len(values), batch_size)
    ]

    def insert_chunk(chunk: list[dict[str, Any]]) -> int:
        collection.insert_many(chunk, ordered=False)
        return len(chunk)

    try:
        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as executor:
            inserted = sum(executor.map(insert_chunk, chunks))
        elapsed = time.perf_counter() - started
        persisted = collection.count_documents({})
    finally:
        collection.drop()
        client.close()
    return {
        "benchmark": "mongo",
        "timestamp_utc": now_iso(),
        "rows_requested": rows,
        "rows_inserted": inserted,
        "rows_persisted": persisted,
        "batch_size": batch_size,
        "pool_size": pool_size,
        "workers": workers,
        "elapsed_seconds": round(elapsed, 6),
        "rows_per_second": round(inserted / elapsed, 2) if elapsed else 0,
        "status": "passed" if persisted == rows else "failed",
    }


def benchmark_kafka(
    settings: Any,
    *,
    rows: int,
    batch_size: int,
    pool_size: int,
    workers: int,
) -> dict[str, Any]:
    del pool_size
    bootstrap = settings.KAFKA_BOOTSTRAP_SERVERS
    topic = f"benchmark.raw.{uuid.uuid4().hex[:12]}"
    admin = AdminClient({"bootstrap.servers": bootstrap})
    future = admin.create_topics(
        [NewTopic(topic, num_partitions=max(workers, 3), replication_factor=1)]
    )[topic]
    try:
        future.result(timeout=30)
    except Exception as exc:
        if "already exists" not in str(exc).lower():
            raise

    def delete_topic() -> None:
        delete_future = admin.delete_topics([topic], operation_timeout=30)[topic]
        try:
            delete_future.result(timeout=30)
        except Exception:
            pass

    def produce(start: int, stop: int) -> int:
        producer = Producer({
            "bootstrap.servers": bootstrap,
            "acks": "all",
            "enable.idempotence": True,
            "compression.type": "none",
            "linger.ms": 5,
            "batch.num.messages": batch_size,
        })
        for index in range(start, stop):
            producer.produce(
                topic,
                key=f"benchmark:{index}".encode(),
                value=b'{"source":"benchmark"}',
            )
        remaining = producer.flush(60)
        producer.close()
        if remaining:
            raise RuntimeError(f"{remaining} Kafka messages were not delivered")
        return stop - start

    boundaries = [
        (rows * worker // workers, rows * (worker + 1) // workers)
        for worker in range(workers)
    ]
    try:
        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as executor:
            delivered = sum(
                executor.map(lambda pair: produce(*pair), boundaries)
            )
        elapsed = time.perf_counter() - started
    except Exception:
        delete_topic()
        raise

    consumer = Consumer({
        "bootstrap.servers": bootstrap,
        "group.id": f"benchmark-reader-{uuid.uuid4().hex[:12]}",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })
    try:
        consumer.subscribe([topic])
        received = 0
        deadline = time.monotonic() + 120
        while received < rows and time.monotonic() < deadline:
            message = consumer.poll(1)
            if message is None:
                continue
            if message.error():
                raise RuntimeError(str(message.error()))
            received += 1
    finally:
        consumer.close()
        delete_topic()
    return {
        "benchmark": "kafka",
        "timestamp_utc": now_iso(),
        "rows_requested": rows,
        "rows_inserted": delivered,
        "rows_persisted": received,
        "batch_size": batch_size,
        "pool_size": None,
        "workers": workers,
        "elapsed_seconds": round(elapsed, 6),
        "rows_per_second": round(delivered / elapsed, 2) if elapsed else 0,
        "status": "passed" if delivered == rows and received == rows else "failed",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=2000)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--pool-size", type=int, default=4)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.rows <= 0 or args.repetitions != 3 or args.pool_size <= 0:
        raise SystemExit("rows and pool-size must be positive; repetitions must be 3")

    settings = load_settings()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    benchmarkers = {
        "postgres": benchmark_postgres,
        "mongo": benchmark_mongo,
        "kafka": benchmark_kafka,
    }
    summary: dict[str, Any] = {
        "generated_at_utc": now_iso(),
        "rows": args.rows,
        "repetitions": args.repetitions,
        "fixed_pool_size": args.pool_size,
    }
    for name, benchmarker in benchmarkers.items():
        batch_cases = [100, 200, 500, 1000, 2000, 3000, 4000, 5000]
        batch_results = run_phase(
            settings,
            benchmarker=benchmarker,
            output=output / name / "phase-1-batch",
            rows=args.rows,
            repetitions=args.repetitions,
            cases=[
                {"batch_size": batch, "pool_size": args.pool_size, "workers": 4}
                for batch in batch_cases
            ],
            phase="batch",
        )
        best_batch = max(
            batch_results,
            key=lambda result: result["median_rows_per_second"],
        )["batch_size"]
        worker_results = run_phase(
            settings,
            benchmarker=benchmarker,
            output=output / name / "phase-2-workers",
            rows=args.rows,
            repetitions=args.repetitions,
            cases=[
                {
                    "batch_size": best_batch,
                    "pool_size": args.pool_size,
                    "workers": workers,
                }
                for workers in [1, 2, 4, 6, 8]
            ],
            phase="workers",
        )
        best_worker = max(
            worker_results,
            key=lambda result: result["median_rows_per_second"],
        )["workers"]
        if name == "kafka":
            pool_results = []
            pool_status = "not_applicable"
        else:
            pool_results = run_phase(
                settings,
                benchmarker=benchmarker,
                output=output / name / "phase-3-pool",
                rows=args.rows,
                repetitions=args.repetitions,
                cases=[
                    {
                        "batch_size": best_batch,
                        "pool_size": pool_size,
                        "workers": best_worker,
                    }
                    for pool_size in [1, 2, 4, 6, 8]
                ],
                phase="pool",
            )
            pool_status = "measured"
        summary[name] = {
            "phase_1_batch_results": batch_results,
            "best_batch_size": best_batch,
            "phase_2_worker_results": worker_results,
            "best_worker_count": best_worker,
            "phase_3_pool_status": pool_status,
            "phase_3_pool_results": pool_results,
        }
    write_json(output / "summary.json", summary)
    print(f"Benchmark complete. Results: {output}")


def run_phase(
    settings: Any,
    *,
    output: Path,
    rows: int,
    repetitions: int,
    benchmarker: Any,
    cases: list[dict[str, int]],
    phase: str,
) -> list[dict[str, Any]]:
    output.mkdir(parents=True, exist_ok=True)
    summaries = []
    for case in cases:
        runs = []
        case_name = (
            f"{phase}-b{case['batch_size']}-p{case['pool_size']}"
            f"-w{case['workers']}"
        )
        for repetition in range(1, repetitions + 1):
            result = benchmarker(settings, rows=rows, **case)
            result.update(
                {
                    "phase": phase,
                    "case": case_name,
                    "repetition": repetition,
                }
            )
            runs.append(result)
            write_json(
                output / f"{case_name}-run-{repetition}.json",
                result,
            )
        median = statistics.median(
            run["rows_per_second"] for run in runs
        )
        summary = {
            **case,
            "phase": phase,
            "case": case_name,
            "repetitions": repetitions,
            "median_rows_per_second": round(median, 2),
            "runs": runs,
        }
        summaries.append(summary)
        write_json(output / f"{case_name}-median.json", summary)
    return summaries


if __name__ == "__main__":
    main()
