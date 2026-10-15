
import psycopg

from tests.integration.test_environment.helpers import (
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
    mongo_collection,
    new_event,
    store_clean_in_postgres,
    store_raw_in_mongo,
)


def test_mongo_write_is_idempotent():
    event = new_event()

    store_raw_in_mongo(event)
    store_raw_in_mongo(event)

    client, collection = mongo_collection()
    try:
        count = collection.count_documents({"_id": event["event_id"]})
        assert count == 1
    finally:
        client.close()


def test_postgres_write_is_idempotent():
    event = new_event()

    store_clean_in_postgres(event)
    store_clean_in_postgres(event)

    with psycopg.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        connect_timeout=5,
    ) as conn:
        count = conn.execute(
            """
            SELECT COUNT(*)
            FROM smoke_events
            WHERE event_id = %s
            """,
            (event["event_id"],),
        ).fetchone()[0]

    assert count == 1
