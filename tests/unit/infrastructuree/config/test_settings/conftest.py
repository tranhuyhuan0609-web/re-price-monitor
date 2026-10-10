import pytest

from src.infrastructure.config.settings import Settings


@pytest.fixture
def valid_settings_data():
 
    return {
        "ENV": "dev",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": 5432,
        "POSTGRES_USER": "test_user",
        "POSTGRES_PASSWORD": "fake_password",
        "POSTGRES_DB": "realestate",
        "MONGO_HOST": "localhost",
        "MONGO_PORT": 27017,
        "MONGO_USER": "test_user",
        "MONGO_PASSWORD": "fake_password",
        "MONGO_DB": "realestate_raw",
        "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
        "KAFKA_RAW_TOPIC": "realestate.raw",
        "KAFKA_DLQ_TOPIC": "realestate.dlq",
        "KAFKA_GROUP_RAW_WRITER": "raw-writer",
        "KAFKA_GROUP_CLEAN_PROCESSOR": "clean-processor",
        "CRAWLER_LOG_LEVEL": "INFO",
    }