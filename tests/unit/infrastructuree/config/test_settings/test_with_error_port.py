import pytest
from pydantic import ValidationError

from src.infrastructure.config.settings import Settings
def test_settings_reject_invalid_postgres_port(valid_settings_data):
    invalid_data = valid_settings_data.copy()
    invalid_data["POSTGRES_PORT"] = 543277

    with pytest.raises(ValidationError) as exc_info:
        Settings(**invalid_data)

    # assert "POSTGRES_PORT" in str(exc_info.value)