# from src.infrastructure.database.postgres_pool_factory import PostgresPoolFactory
# import pytest
# @pytest.mark.parametrize(
#     "host, port, user, password, dbname",
#     [
#         ("", 5432, "test_user", "test_password", "test_db"),
#         ("localhost", 0, "test_user", "test_password", "test_db"),
#         ("localhost", 5432, "", "test_password", "test_db"),
#         ("localhost", 5432, "test_user", "", "test_db"),
#         ("localhost", 5432, "test_user", "test_password", ""),
#         ("localhost", True, "test_user", "test_password", "test_db"),
#     ]
# )
# def test_with_invalid_connection_params(host, port, user, password, dbname):
#     with pytest.raises(ValueError):
#         PostgresPoolFactory(
#             host=host,
#             port=port,
#             user=user,
#             password=password,
#             dbname=dbname,
#         )