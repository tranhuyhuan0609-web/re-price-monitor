import pytest
from src.infrastructure.config.settings import load_settings

def test_load_settings_returns_cached_instance(
    monkeypatch,
    tmp_path,
):
    import src.infrastructure.config.settings as settings_module

    env_file = tmp_path / ".env.dev"
    env_file.write_text(
        "\n".join([
            "POSTGRES_HOST=localhost",
            "POSTGRES_PORT=5432",
            "POSTGRES_USER=test_user",
            "POSTGRES_PASSWORD=fake_password",
            "POSTGRES_DB=realestate",
            "MONGO_HOST=localhost",
            "MONGO_PORT=27017",
            "MONGO_USER=test_user",
            "MONGO_PASSWORD=fake_password",
            "MONGO_DB=realestate_raw",
            "KAFKA_BOOTSTRAP_SERVERS=localhost:9092",
            "KAFKA_RAW_TOPIC=realestate.raw",
            "KAFKA_DLQ_TOPIC=realestate.dlq",
            "KAFKA_GROUP_RAW_WRITER=raw-writer",
            "KAFKA_GROUP_CLEAN_PROCESSOR=clean-processor",
            "CRAWLER_LOG_LEVEL=INFO",
        ]),
        encoding="utf-8",
    )

    monkeypatch.setattr(settings_module, "BASE_DIR", tmp_path)
    monkeypatch.setenv("ENV", "dev")
    load_settings.cache_clear()

    try:
        first = load_settings()
        second = load_settings()

        assert first is second
    finally:
        load_settings.cache_clear()
