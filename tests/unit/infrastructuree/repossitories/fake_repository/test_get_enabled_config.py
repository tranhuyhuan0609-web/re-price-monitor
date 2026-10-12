from src.domain.entities.crawler_config import CrawlerConfig
async def test_get_enabled_configs_returns_empty_list_when_repository_is_empty(
    fake_config_repository,
):
    result = await fake_config_repository.get_enabled_configs()

    assert result == []


async def test_get_enabled_configs_returns_only_enabled_configs(
    fake_config_repository,
    valid_config,
):
    enabled_config = valid_config
    disabled_config = CrawlerConfig(
        **{
            **valid_config.model_dump(),
            "site_id": "disabled_site",
            "name": "Disabled Site",
            "enabled": False,
        }
    )

    await fake_config_repository.create_config(enabled_config)
    await fake_config_repository.create_config(disabled_config)

    result = await fake_config_repository.get_enabled_configs()

    assert result == [enabled_config]
    assert all(config.enabled for config in result)


async def test_get_enabled_configs_returns_all_enabled_configs(
    fake_config_repository,
    valid_config,
):
    second_config = CrawlerConfig(
        **{
            **valid_config.model_dump(),
            "site_id": "second_site",
            "name": "Second Site",
            "enabled": True,
        }
    )

    await fake_config_repository.create_config(valid_config)
    await fake_config_repository.create_config(second_config)

    result = await fake_config_repository.get_enabled_configs()

    assert len(result) == 2
    assert result == [valid_config, second_config]
