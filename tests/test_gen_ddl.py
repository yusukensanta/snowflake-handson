from pathlib import Path

from hanbit_gen.ddl import raw_ddl
from hanbit_gen.schema import DOMAINS, SCHEMAS


def test_ddl_has_batch_and_stream_table_per_domain():
    ddl = raw_ddl()
    for d in DOMAINS:
        assert f"CREATE TABLE IF NOT EXISTS HANBIT_RAW.{d.upper()}.{d.upper()} (" in ddl
        assert f"CREATE TABLE IF NOT EXISTS HANBIT_RAW.{d.upper()}.{d.upper()}_STREAM (" in ddl


def test_ddl_contains_every_column_with_its_type():
    ddl = raw_ddl()
    for c in SCHEMAS["lending"]:
        assert f"{c.name.upper()} {c.type}" in ddl


def test_committed_sql_file_is_in_sync_with_schema():
    committed = Path(__file__).parents[1] / "sql" / "raw_tables.sql"
    assert committed.read_text() == raw_ddl()
