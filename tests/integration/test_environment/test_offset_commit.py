
import pytest

from tests.integration.test_environment.helpers import (
    make_consumer,
    new_event,
    publish_event,
    store_clean_in_postgres,
    wait_for_event,
)


def test_failed_storage_does_not_commit_and_event_is_replayed():
    event = new_event()
    group_id = f"offset-test-{event['event_id']}"

    publish_event(event)

    # Lần 1: mô phỏng database gặp lỗi.
    consumer1 = make_consumer(group_id)
    try:
        received, _ = wait_for_event(
            consumer1,
            event["event_id"],
        )
        assert received == event

        with pytest.raises(RuntimeError, match="Simulated DB failure"):
            raise RuntimeError("Simulated DB failure")

        # Cố ý KHÔNG commit offset.
    finally:
        consumer1.close()

    # Lần 2: dùng lại group ID, event phải được đọc lại.
    consumer2 = make_consumer(group_id)
    try:
        replayed, kafka_message = wait_for_event(
            consumer2,
            event["event_id"],
        )

        assert replayed == event

        # Lưu thành công rồi mới commit.
        store_clean_in_postgres(replayed)

        consumer2.commit(
            message=kafka_message,
            asynchronous=False,
        )
    finally:
        consumer2.close()
