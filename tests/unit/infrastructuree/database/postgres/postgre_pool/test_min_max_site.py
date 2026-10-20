# from src.infrastructure.database.postgres_pool_factory import PostgresPoolFactory
# import pytest
# def test_with_valid_min_max_size():
#     factory = PostgresPoolFactory(
#         host="localhost",
#         port=5432,
#         user="test_user",
#         password="test_password",
#         dbname="test_db",
#         min_size=1,
#         max_size=5,
#     )
#     assert factory._min_size == 1
#     assert factory._max_size == 5
# @pytest.mark.parametrize(
#     "min_size, max_size",
#     [
#         (0, 5),  # min_size less than 1
#         (1, 0),  # max_size less than 1
#         (5, 3),  # min_size greater than max_size
#         (True, 5),  # min_size is a boolean
#         (3, False),  # max_size is a boolean
#     ],
# )
# def test_with_invalid_min_max_size(min_size, max_size):
#     with pytest.raises(ValueError):
#         PostgresPoolFactory(
#             host="localhost",
#             port=5432,
#             user="test_user",
#             password="test_password",
#             dbname="test_db",
#             min_size=min_size,
#             max_size=max_size,
#         )
