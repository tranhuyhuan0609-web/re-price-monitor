import pytest
from pydantic import ValidationError

from src.infrastructure.config.settings import Settings


def test_settings_reject_partial_exchange_rate_configuration(
    valid_settings_data,
):
    config_data = valid_settings_data.copy()
    config_data["FX_RATE_URL"] = "https://rates.example.test/latest"
    config_data["FX_RATE_SOURCE"] = None

    with pytest.raises(ValidationError, match="configured together"):
        Settings(**config_data)


def test_settings_accept_complete_exchange_rate_configuration(
    valid_settings_data,
):
    config_data = valid_settings_data | {
        "FX_RATE_URL": "https://rates.example.test/latest",
        "FX_RATE_SOURCE": "rates.example.test",
    }

    settings = Settings(**config_data)

    assert settings.FX_RATE_URL.endswith("/latest")
