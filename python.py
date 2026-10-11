from pathlib import Path

path = Path("create_silver_schema_v1.sql")
sql = path.read_text(encoding="utf-8")
sql = sql.replace("\u00a0", " ")
path.write_text(sql, encoding="utf-8")