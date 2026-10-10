
import pytest

from src.infrastructure.config.settings import Settings

def test_settings_accept_valid_configuration(valid_settings_data):

    settings = Settings(**valid_settings_data)

    assert settings.ENV == "dev"
    assert settings.POSTGRES_PORT == 5432
    assert settings.MONGO_PORT == 27017
    assert settings.KAFKA_GROUP_RAW_WRITER == "raw-writer"
    assert settings.KAFKA_GROUP_CLEAN_PROCESSOR == "clean-processor"
