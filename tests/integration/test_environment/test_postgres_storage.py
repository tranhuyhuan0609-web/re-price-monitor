
# import psycopg

# from tests.integration.test_environment.helpers import (
#     POSTGRES_DB,
#     POSTGRES_HOST,
#     POSTGRES_PASSWORD,
#     POSTGRES_PORT,
#     POSTGRES_USER,
#     new_event,
#     store_clean_in_postgres,
# )


# def test_postgres_stores_clean_event():
#     event = new_event()

#     store_clean_in_postgres(event)

#     with psycopg.connect(
#         host=POSTGRES_HOST,
#         port=POSTGRES_PORT,
#         dbname=POSTGRES_DB,
#         user=POSTGRES_USER,
#         password=POSTGRES_PASSWORD,
#         connect_timeout=5,
#     ) as conn:
#         row = conn.execute(
#             """
#             SELECT event_id, price_raw
#             FROM smoke_events
#             WHERE event_id = %s
#             """,
#             (event["event_id"],),
#         ).fetchone()

#     assert row == (event["event_id"], event["price_raw"])
