
import json
import os
import time
import uuid

import psycopg
import pytest
from confluent_kafka import Consumer, Producer
from confluent_kafka.admin import AdminClient, NewTopic
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

TOPIC = "smoke.test"
BROKERS = "localhost:9092"


@pytest.fixture(scope="module", autouse=True)
def create_topic():
    admin = AdminClient({"bootstrap.servers": BROKERS})
    futures = admin.create_topics([NewTopic(TOPIC, num_partitions=3, replication_factor=1)])
    for f in futures.values():
        try:
            f.result()
        except Exception:
            pass  


def consume_one(group_id: str, expected_id: str, timeout: float = 15.0) -> dict:
    
    consumer = Consumer({
        "bootstrap.servers": BROKERS,
        "group.id": group_id,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })
    consumer.subscribe([TOPIC])
    deadline = time.time() + timeout
    try:
        while time.time() < deadline:
            msg = consumer.poll(1.0)
            if msg is None or msg.error():
                continue
            data = json.loads(msg.value())
            if data["event_id"] == expected_id:
                return data
    finally:
        consumer.close()
    raise AssertionError(f"Group {group_id} dont receive message {expected_id}")


def test_kafka_to_mongo_and_postgres():
    event_id = str(uuid.uuid4())
    message = {"event_id": event_id, "source": "smoke", "price_raw": "3,5 tỷ"}

   
    producer = Producer({"bootstrap.servers": BROKERS, "enable.idempotence": True})
    producer.produce(TOPIC, key="smoke:1", value=json.dumps(message))
    producer.flush()

    
    got_a = consume_one("smoke-raw-writer", event_id)
    got_b = consume_one("smoke-clean-processor", event_id)
    assert got_a == got_b == message


    mongo = MongoClient(
        f"mongodb://{os.getenv('MONGO_USER')}:{os.getenv('MONGO_PASSWORD')}@localhost:27017"
    )
    coll = mongo.smoke.raw
    coll.replace_one({"_id": got_a["event_id"]}, got_a, upsert=True)
    assert coll.count_documents({"_id": event_id}) == 1

    with psycopg.connect(
        host="localhost", dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"), password=os.getenv("POSTGRES_PASSWORD"),
    ) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS smoke (event_id TEXT PRIMARY KEY, price_raw TEXT)")
        conn.execute(
            "INSERT INTO smoke VALUES (%s, %s) ON CONFLICT (event_id) DO NOTHING",
            (got_b["event_id"], got_b["price_raw"]),
        )
        count = conn.execute("SELECT count(*) FROM smoke WHERE event_id = %s", (event_id,)).fetchone()[0]
        assert count == 1