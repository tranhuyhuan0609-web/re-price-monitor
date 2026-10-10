
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import quote

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[3]

Environment = Literal["dev", "test", "prod"]


class BootstrapSettings(BaseSettings):
    """Load the environment name used to select the application configuration."""

    ENV: Environment = "dev"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


class Settings(BaseSettings):
    """Application configuration for databases, Kafka, and logging."""

    ENV: Environment

    # PostgreSQL
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = Field(default=5432, ge=1, le=65535)
    POSTGRES_USER: str
    POSTGRES_PASSWORD: SecretStr
    POSTGRES_DB: str

    # MongoDB
    MONGO_HOST: str = "localhost"
    MONGO_PORT: int = Field(default=27017, ge=1, le=65535)
    MONGO_USER: str
    MONGO_PASSWORD: SecretStr
    MONGO_DB: str

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = Field(min_length=1)
    KAFKA_RAW_TOPIC: str = Field(min_length=1)
    KAFKA_DLQ_TOPIC: str = Field(min_length=1)
    KAFKA_GROUP_RAW_WRITER: str = Field(min_length=1)
    KAFKA_GROUP_CLEAN_PROCESSOR: str = Field(min_length=1)

    # Application logging
    CRAWLER_LOG_LEVEL: Literal[
        "DEBUG", "INFO", "WARNING", "ERROR"
    ] = "INFO"

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        validate_default=True,
    )

    @model_validator(mode="after")
    def validate_configuration(self) -> "Settings":
        """Validate relationships between configuration values."""

        if (
            self.KAFKA_GROUP_RAW_WRITER
            == self.KAFKA_GROUP_CLEAN_PROCESSOR
        ):
            raise ValueError(
                "RAW and CLEAN consumers must use different consumer groups."
            )

        if self.KAFKA_RAW_TOPIC == self.KAFKA_DLQ_TOPIC:
            raise ValueError(
                "The RAW topic and DLQ topic must be different."
            )

        if self.ENV == "test":
            for field_name in ("POSTGRES_DB", "MONGO_DB"):
                database_name = getattr(self, field_name)

                if not database_name.endswith("_test"):
                    raise ValueError(
                        f"{field_name} must end with '_test' "
                        "when ENV='test'."
                    )

        return self

    @property
    def postgres_dsn(self) -> str:
        """Build a PostgreSQL connection string."""

        username = quote(self.POSTGRES_USER, safe="")
        password = quote(
            self.POSTGRES_PASSWORD.get_secret_value(),
            safe="",
        )
        database = quote(self.POSTGRES_DB, safe="")

        return (
            f"postgresql://{username}:{password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{database}"
        )

    @property
    def mongo_uri(self) -> str:
        """Build a MongoDB URI using the admin authentication database."""

        username = quote(self.MONGO_USER, safe="")
        password = quote(
            self.MONGO_PASSWORD.get_secret_value(),
            safe="",
        )

        return (
            f"mongodb://{username}:{password}"
            f"@{self.MONGO_HOST}:{self.MONGO_PORT}/"
            f"?authSource=admin"
        )


def _load_settings() -> Settings:
    """Load settings for the selected environment."""

    environment = BootstrapSettings().ENV
    env_file = BASE_DIR / f".env.{environment}"

    if env_file.is_file():
        return Settings(_env_file=env_file, ENV=environment)

    if environment == "prod":
        return Settings(_env_file=None, ENV=environment)

    raise FileNotFoundError(
        f"Configuration file not found: {env_file}"
    )


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    """Return a cached application settings instance."""

    return _load_settings()
