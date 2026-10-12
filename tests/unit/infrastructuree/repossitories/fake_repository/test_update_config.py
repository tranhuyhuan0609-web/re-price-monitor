import pytest
from src.application.exceptions.config_exceptions import (
    ConfigNotFoundError,
    ConfigIdentityMismatchError,
)
from src.domain.entities.crawler_config import CrawlerConfig


async def test_update_config_updates_existing_config(
    fake_config_repository,
    valid_config,
):
    await fake_config_repository.create_config(valid_config)

    updated_config = CrawlerConfig(
        **{
            **valid_config.model_dump(),
            "name": "Updated Name",
        }
    )

    await fake_config_repository.update_config(
        valid_config.site_id,
        updated_config,
    )

    result = await fake_config_repository.get_config(
        valid_config.site_id
    )

    assert result == updated_config
    assert result.name == "Updated Name"


async def test_update_config_raises_when_config_does_not_exist(
    fake_config_repository,
    valid_config,
):
    with pytest.raises(ConfigNotFoundError):
        await fake_config_repository.update_config(
            valid_config.site_id,
            valid_config,
        )


async def test_update_config_raises_when_site_ids_do_not_match(
    fake_config_repository,
    valid_config,
):
    mismatched_config = CrawlerConfig(
        **{
            **valid_config.model_dump(),
            "site_id": "another_site",
        }
    )

    with pytest.raises(ConfigIdentityMismatchError):
        await fake_config_repository.update_config(
            valid_config.site_id,
            mismatched_config,
        )
