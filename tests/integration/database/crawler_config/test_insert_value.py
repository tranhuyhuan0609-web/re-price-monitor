import psycopg
import pytest
from psycopg.types.json import Jsonb


async def test_insert_valid_crawler_config(db_connection, valid_config):
    async with db_connection.cursor() as cur:
        config_dict = valid_config.model_dump(mode="json")

        result = await cur.execute(
            """
            INSERT INTO crawler_configs (
                site_id, name, enabled, config_json
            )
            VALUES (%s, %s, %s, %s)
            RETURNING site_id, name, enabled, config_json
            """,
            (
                valid_config.site_id,
                valid_config.name,
                valid_config.enabled,
                Jsonb(config_dict),
            ),
        )

        row = await result.fetchone()

    assert row is not None
    assert row[0] == valid_config.site_id
    assert row[1] == valid_config.name
    assert row[2] is valid_config.enabled
    assert row[3] == config_dict


async def test_insert_rejects_mismatched_enabled(db_connection, valid_config):
    config_json = {
        **valid_config.model_dump(mode="json"),
        "enabled": False,
    }

    with pytest.raises(psycopg.errors.CheckViolation):
        async with db_connection.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO crawler_configs (site_id, name, enabled, config_json)
                VALUES (%s, %s, %s, %s)
                """,
                    (
                        valid_config.site_id,
                        valid_config.name,
                        valid_config.enabled,
                        Jsonb(config_json),
                    ),
                )


async def test_insert_rejects_mismatched_site_id(db_connection, valid_config):
    config_json = {
        **valid_config.model_dump(mode="json"),
        "site_id": "another-site",
    }

    with pytest.raises(psycopg.errors.CheckViolation):
        async with db_connection.cursor() as cur:
                await cur.execute(
                """
                INSERT INTO crawler_configs (site_id, name, enabled, config_json)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    valid_config.site_id,
                    valid_config.name,
                    valid_config.enabled,
                    Jsonb(config_json),
                ),
            )
