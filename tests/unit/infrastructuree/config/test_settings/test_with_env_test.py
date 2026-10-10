from src.infrastructure.config.settings import Settings
import pytest
from pydantic import ValidationError

def test_settings_reject_test_database_without_suffix(
    valid_settings_data,
):
    config_data = valid_settings_data.copy()
    config_data["ENV"] = "test"
    config_data["POSTGRES_DB"] = "realestate"
    config_data["MONGO_DB"] = "realestate_raw"

    with pytest.raises(ValidationError):
        Settings(**config_data)