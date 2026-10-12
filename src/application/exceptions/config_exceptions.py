class ConfigNotFoundError(Exception):
    """Raised when the configuration file is not found."""
    pass
class ConfigAlreadyExistsError(Exception):
    """Raised when the configuration file already exists."""
    pass
class ConfigIdentityMismatchError(Exception):
    """Raised when the configuration file identity does not match."""
    pass
class ConfigRepositoryError(Exception):
    """Raised when there is an error in the configuration repository."""
    pass