import psycopg
import pytest

from src.application.exceptions.config_exceptions import (
    ConfigAlreadyExistsError,
    ConfigNotFoundError,
)
from src.domain.entities.crawler_config import CrawlerConfig
from src.infrastructure.database.postgres_config_repository import (
    ConfigCorruptedError,
    PostgresConfigRepository,
)


async def test_create_and_get_config(repository, valid_config):
    await repository.create_config(valid_config)

    actual = await repository.get_config(valid_config.site_id)

    assert isinstance(actual, CrawlerConfig)
    assert actual == valid_config


async def test_create_duplicate_config_raises_error(
    repository,
    valid_config,
):
    await repository.create_config(valid_config)

    with pytest.raises(ConfigAlreadyExistsError):
        await repository.create_config(valid_config)


async def test_get_missing_config_raises_error(repository):
    with pytest.raises(ConfigNotFoundError):
        await repository.get_config("missing-site")


async def test_get_enabled_configs_returns_only_enabled(
    repository,
    valid_config,
    disabled_config,
):
    await repository.create_config(valid_config)
    await repository.create_config(disabled_config)

    configs = await repository.get_enabled_configs()

    site_ids = {config.site_id for config in configs}

    assert valid_config.site_id in site_ids
    assert disabled_config.site_id not in site_ids

async def test_update_config(repository, valid_config):
    await repository.create_config(valid_config)

    updated_config = valid_config.model_copy(
        update={"name": "Updated crawler name"}
    )

    await repository.update_config(
        site_id=valid_config.site_id,
        config=updated_config,
    )

    actual = await repository.get_config(valid_config.site_id)

    assert actual.name == "Updated crawler name"
    assert actual.site_id == valid_config.site_id


async def test_update_missing_config_raises_error(
    repository,
    valid_config,
):
    with pytest.raises(ConfigNotFoundError):
        await repository.update_config(
            site_id=valid_config.site_id,
            config=valid_config,
        )

async def test_update_identity_mismatch_raises_error(
    repository,
    valid_config,
    another_valid_config,
):
    with pytest.raises(ValueError, match="site_id"):
        await repository.update_config(
            site_id=valid_config.site_id,
            config=another_valid_config,
        )


async def test_delete_config(repository, valid_config):
    await repository.create_config(valid_config)

    await repository.delete_config(valid_config.site_id)

    with pytest.raises(ConfigNotFoundError):
        await repository.get_config(valid_config.site_id)


async def test_delete_missing_config_raises_error(repository):
    with pytest.raises(ConfigNotFoundError):
        await repository.delete_config("missing-site")


async def test_get_config_rejects_corrupted_jsonb(
    repository,
    valid_config,
    db_pool,
):
    await repository.create_config(valid_config)

    # Đánh dấu kỳ vọng khối code này bắt buộc phải văng ra lỗi CheckViolation từ DB
    with pytest.raises(psycopg.errors.CheckViolation):
        async with db_pool.connection() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    UPDATE crawler_configs
                    SET config_json = jsonb_set(
                        config_json,
                        '{site_id}',
                        '"wrong-site-id"'::jsonb
                    )
                    WHERE site_id = %s
                    """,
                    (valid_config.site_id,),
                )