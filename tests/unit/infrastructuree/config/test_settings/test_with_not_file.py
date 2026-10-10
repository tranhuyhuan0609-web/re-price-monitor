import pytest
from src.infrastructure.config.settings import load_settings
def test_load_settings_raises_when_env_file_missing(
    monkeypatch,
    tmp_path,
):
    import src.infrastructure.config.settings as settings_module

    monkeypatch.setattr(settings_module, "BASE_DIR", tmp_path)
    monkeypatch.setenv("ENV", "dev")
    monkeypatch.delenv("POSTGRES_DB", raising=False)
    load_settings.cache_clear()

    try:
        with pytest.raises(FileNotFoundError):
            load_settings()
    finally:
        load_settings.cache_clear()