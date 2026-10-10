from src.infrastructure.config.settings import Settings
import pytest
from pydantic import ValidationError
def test_settings_with_raw_equals_dlq(valid_settings_data):
    
    invalid_data = valid_settings_data.copy()
    invalid_data["KAFKA_RAW_TOPIC"] = "same-topic"
    invalid_data["KAFKA_DLQ_TOPIC"] = "same-topic"

    with pytest.raises(ValidationError):
        Settings(**invalid_data)