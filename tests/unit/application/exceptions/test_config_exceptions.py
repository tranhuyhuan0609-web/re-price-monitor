
import pytest

from src.application.exceptions.config_exceptions import (
    ConfigAlreadyExistsError,
    ConfigIdentityMismatchError,
    ConfigNotFoundError,
    ConfigRepositoryError,
)


def test_config_not_found_error_is_exception():
    assert issubclass(ConfigNotFoundError, Exception)


def test_config_not_found_error_can_be_raised_and_caught():
    with pytest.raises(ConfigNotFoundError):
        raise ConfigNotFoundError("Configuration 'batdongsan' not found")
def test_config_already_exists_error_can_be_raised_and_caught():
    with pytest.raises(ConfigAlreadyExistsError):
        raise ConfigAlreadyExistsError(
            "Configuration 'batdongsan' already exists"
        )


def test_config_already_exists_error_is_not_config_not_found_error():
    assert not issubclass(
        ConfigAlreadyExistsError,
        ConfigNotFoundError,
    )

def test_config_identity_mismatch_error_can_be_raised_and_caught():
    with pytest.raises(ConfigIdentityMismatchError):
        raise ConfigIdentityMismatchError(
            "Configuration site_id does not match the requested site_id"
        )


def test_config_identity_mismatch_error_is_not_config_not_found_error():
    assert not issubclass(
        ConfigIdentityMismatchError,
        ConfigNotFoundError,
    )

def test_config_repository_error_can_be_raised_and_caught():
    with pytest.raises(ConfigRepositoryError):
        raise ConfigRepositoryError("Database connection failed")


def test_config_repository_error_is_not_config_not_found_error():
    assert not issubclass(
        ConfigRepositoryError,
        ConfigNotFoundError,
    )