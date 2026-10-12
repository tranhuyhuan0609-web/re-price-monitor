
import pytest
from src.application.exceptions.config_exceptions import (
    ConfigAlreadyExistsError,
)


async def test_create_config_saves_new_config(
    fake_config_repository,
    valid_config,
):
    await fake_config_repository.create_config(valid_config)

    result = await fake_config_repository.get_config(
        valid_config.site_id
    )

    assert result == valid_config


async def test_create_config_raises_when_site_id_already_exists(
    fake_config_repository,
    valid_config,
):
    await fake_config_repository.create_config(valid_config)

    with pytest.raises(ConfigAlreadyExistsError):
        await fake_config_repository.create_config(valid_config)

    result = await fake_config_repository.get_config(
        valid_config.site_id
    )
    assert result == valid_config
