import pytest
from src.application.exceptions.config_exceptions import ConfigNotFoundError
async def test_delete_config_removes_existing_config(
    fake_config_repository,
    valid_config,
):
    await fake_config_repository.create_config(valid_config)

    await fake_config_repository.delete_config(valid_config.site_id)

    with pytest.raises(ConfigNotFoundError):
        await fake_config_repository.get_config(valid_config.site_id)


async def test_delete_config_raises_when_config_does_not_exist(
    fake_config_repository,
):
    with pytest.raises(ConfigNotFoundError):
        await fake_config_repository.delete_config("unknown_site")
