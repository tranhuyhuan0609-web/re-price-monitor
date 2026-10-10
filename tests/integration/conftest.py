
import pytest

from tests.integration.helpers import ensure_topic


@pytest.fixture(scope="session", autouse=True)
def kafka_topic_ready():
    ensure_topic()
