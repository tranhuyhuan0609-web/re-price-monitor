from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool


class PostgresPoolFactory:
    """Create an asynchronous PostgreSQL connection pool."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        dbname: str,
        min_size: int = 1,
        max_size: int = 10,
    ) -> None:
        self._validate_connection_params(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=dbname,
        )
        self._validate_pool_size(min_size=min_size, max_size=max_size)

        self._host = host.strip()
        self._port = port
        self._user = user.strip()
        self._password = password
        self._dbname = dbname.strip()
        self._min_size = min_size
        self._max_size = max_size

    @staticmethod
    def _validate_connection_params(
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        dbname: str,
    ) -> None:
        string_params = {
            "host": host,
            "user": user,
            "password": password,
            "dbname": dbname,
        }

        for name, value in string_params.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string.")

        if isinstance(port, bool) or not isinstance(port, int):
            raise ValueError("port must be an integer.")

        if not 1 <= port <= 65535:
            raise ValueError("port must be between 1 and 65535.")

    @staticmethod
    def _validate_pool_size(
        *,
        min_size: int,
        max_size: int,
    ) -> None:
        if isinstance(min_size, bool) or not isinstance(min_size, int):
            raise ValueError("min_size must be an integer.")

        if isinstance(max_size, bool) or not isinstance(max_size, int):
            raise ValueError("max_size must be an integer.")

        if min_size < 1:
            raise ValueError("min_size must be at least 1.")

        if max_size < min_size:
            raise ValueError("max_size must be greater than or equal to min_size.")

    def create_pool(self) -> AsyncConnectionPool:
        conninfo = make_conninfo(
            "",
            host=self._host,
            port=self._port,
            user=self._user,
            password=self._password,
            dbname=self._dbname,
        )

        return AsyncConnectionPool(
            conninfo=conninfo,
            min_size=self._min_size,
            max_size=self._max_size,
            kwargs={"row_factory": dict_row},
            open=False,
        )
