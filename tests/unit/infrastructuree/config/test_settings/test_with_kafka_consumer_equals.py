from src.infrastructure.config.settings import Settings
import pytest
from pydantic import ValidationError
def test_settings_with_kafka_consumer_equals(valid_settings_data):
    
    invalid_data = valid_settings_data.copy()
    invalid_data["KAFKA_GROUP_RAW_WRITER"] = "same-group"
    invalid_data["KAFKA_GROUP_CLEAN_PROCESSOR"] = "same-group"

    with pytest.raises(ValidationError):
        Settings(**invalid_data)

    