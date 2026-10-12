
import pytest

from src.application.exceptions.config_exceptions import ConfigNotFoundError
async def test_get_config_returns_existing_config(
    fake_config_repository,
    valid_config,
):
    await fake_config_repository.create_config(valid_config)

    result = await fake_config_repository.get_config(
        valid_config.site_id
    )

    assert result == valid_config


async def test_get_config_raises_when_config_does_not_exist(
    fake_config_repository,
):
    with pytest.raises(ConfigNotFoundError):
        await fake_config_repository.get_config("unknown_site")
