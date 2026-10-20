# from unittest.mock import patch

# from psycopg.conninfo import conninfo_to_dict
# from psycopg.rows import dict_row
# from psycopg_pool import AsyncConnectionPool

# from src.infrastructure.database.postgres_pool_factory import (
#     PostgresPoolFactory,
# )


# def test_create_pool_uses_expected_configuration():
#     factory = PostgresPoolFactory(
#         host="localhost",
#         port=5432,
#         user="test_user",
#         password="test@pass word:123",
#         dbname="realestate",
#         min_size=2,
#         max_size=5,
#     )

#     mock_pool = object()

#     with patch(
#         "src.infrastructure.database.postgres_pool_factory.AsyncConnectionPool",
#         return_value=mock_pool,
#     ) as mock_pool_class:
#         pool = factory.create_pool()

#     # 1. Trả về đúng pool được tạo
#     assert pool is mock_pool

#     # 2. Factory gọi AsyncConnectionPool đúng một lần
#     mock_pool_class.assert_called_once()

#     # 3. Lấy cấu hình được truyền vào constructor
#     call_kwargs = mock_pool_class.call_args.kwargs

#     # 4. Kiểm tra connection string có đủ thông tin
#     conn_params = conninfo_to_dict(call_kwargs["conninfo"])

#     assert conn_params["host"] == "localhost"
#     assert conn_params["port"] == "5432"
#     assert conn_params["user"] == "test_user"
#     assert conn_params["password"] == "test@pass word:123"
#     assert conn_params["dbname"] == "realestate"

#     # 5. Kiểm tra cấu hình pool
#     assert call_kwargs["min_size"] == 2
#     assert call_kwargs["max_size"] == 5

#     # 6. Kiểm tra row factory
#     assert call_kwargs["kwargs"]["row_factory"] is dict_row

#     # 7. Pool chưa được mở
#     assert call_kwargs["open"] is False
