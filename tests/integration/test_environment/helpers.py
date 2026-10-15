
import json
import os
import time
import uuid
from pathlib import Path

import psycopg
from confluent_kafka import Consumer, KafkaError, KafkaException, Producer
from confluent_kafka.admin import AdminClient, NewTopic
from dotenv import load_dotenv
from pymongo import MongoClient


PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env.dev")

BROKERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = "smoke.test"

MONGO_USER = os.environ["MONGO_USER"]
MONGO_PASSWORD = os.environ["MONGO_PASSWORD"]
MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = int(os.getenv("MONGO_HOST_PORT", "27017"))

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_HOST_PORT", "5432"))
POSTGRES_DB = os.environ["POSTGRES_DB"]
POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]


def new_event(**overrides) -> dict:
    event = {
        "event_id": str(uuid.uuid4()),
        "source": "integration-test",
        "price_raw": "3,5 tỷ",
    }
    event.update(overrides)
    return event


def ensure_topic() -> None:
    admin = AdminClient({"bootstrap.servers": BROKERS})
    futures = admin.create_topics([
        NewTopic(TOPIC, num_partitions=3, replication_factor=1)
    ])

    for future in futures.values():
        try:
            future.result(timeout=15)
        except KafkaException as exc:
            error = exc.args[0]
            if error.code() != KafkaError.TOPIC_ALREADY_EXISTS:
                raise


def publish_event(event: dict) -> None:
    results = []

    def on_delivery(error, message):
        results.append((error, message))

    producer = Producer({
        "bootstrap.servers": BROKERS,
        "enable.idempotence": True,
    })

    producer.produce(
        TOPIC,
        key=event["event_id"],
        value=json.dumps(event),
        callback=on_delivery,
    )

    pending = producer.flush(15)
    assert pending == 0, "Producer still has messages pending"

    assert results, "No delivery callback received"
    error, message = results[0]

    assert error is None, f"Kafka delivery failed: {error}"
    assert message.topic() == TOPIC


def make_consumer(group_id: str) -> Consumer:
    return Consumer({
        "bootstrap.servers": BROKERS,
        "group.id": group_id,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
        "enable.auto.offset.store": False,
    })


def wait_for_event(
    consumer: Consumer,
    expected_id: str,
    timeout: float = 20,
) -> tuple[dict, object]:
    consumer.subscribe([TOPIC])
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        message = consumer.poll(1.0)

        if message is None:
            continue

        if message.error():
            raise KafkaException(message.error())

        event = json.loads(message.value())

        if event.get("event_id") == expected_id:
            return event, message

    raise AssertionError(f"Event not received: {expected_id}")


def mongo_collection():
    client = MongoClient(
        host=MONGO_HOST,
        port=MONGO_PORT,
        username=MONGO_USER,
        password=MONGO_PASSWORD,
        authSource="admin",
        serverSelectionTimeoutMS=5000,
    )
    return client, client["realestate_raw"]["raw_events"]


def store_raw_in_mongo(event: dict) -> None:
    client, collection = mongo_collection()
    try:
        collection.replace_one(
            {"_id": event["event_id"]},
            {**event, "_id": event["event_id"]},
            upsert=True,
        )
        stored = collection.find_one({"_id": event["event_id"]})
        assert stored is not None
        assert stored["event_id"] == event["event_id"]
        assert stored["price_raw"] == event["price_raw"]
    finally:
        client.close()


def ensure_postgres_table() -> None:
    with psycopg.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        connect_timeout=5,
    ) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS smoke_events (
                event_id TEXT PRIMARY KEY,
                price_raw TEXT NOT NULL
            )
        """)


def store_clean_in_postgres(event: dict) -> None:
    ensure_postgres_table()

    with psycopg.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        connect_timeout=5,
    ) as conn:
        conn.execute(
            """
            INSERT INTO smoke_events (event_id, price_raw)
            VALUES (%s, %s)
            ON CONFLICT (event_id) DO NOTHING
            """,
            (event["event_id"], event["price_raw"]),
        )

        row = conn.execute(
            """
            SELECT event_id, price_raw
            FROM smoke_events
            WHERE event_id = %s
            """,
            (event["event_id"],),
        ).fetchone()

        assert row == (event["event_id"], event["price_raw"])

def consume_and_store(
    group_id: str,
    expected_id: str,
    store_callback,
    timeout: float = 20.0,
) -> dict:
    consumer = make_consumer(group_id)
    deadline = time.monotonic() + timeout

    try:
        consumer.subscribe([TOPIC])

        while time.monotonic() < deadline:
            message = consumer.poll(1.0)

            if message is None:
                continue

            if message.error():
                raise KafkaException(message.error())

            event = json.loads(message.value())

            if event.get("event_id") != expected_id:
                continue

            # Chỉ commit sau khi lưu dữ liệu thành công.
            store_callback(event)

            consumer.commit(
                message=message,
                asynchronous=False,
            )

            return event

        raise AssertionError(
            f"Group {group_id} did not receive event {expected_id}"
        )
    finally:
        consumer.close()
