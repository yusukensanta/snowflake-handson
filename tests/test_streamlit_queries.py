import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "queries", Path(__file__).parents[1] / "apps/streamlit/queries.py")
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)


def test_claims_by_region_sql_is_aggregate_only():
    sql = q.claims_by_region_sql()
    assert "GROUP BY REGION" in sql and "COUNT(*)" in sql
    assert "CUSTOMER" not in sql.upper()


def test_status_filter_is_allowlisted_not_interpolated():
    assert "status = 'paid'" in q.claims_by_region_sql("paid")
    assert "status" not in q.claims_by_region_sql("x'; DROP TABLE t;--").lower().split("where")[-1]


def test_status_allowlist_matches_generator_values():
    import re
    from pathlib import Path
    src = (Path(__file__).parents[1] / "src/hanbit_gen/generator.py").read_text()
    claims_line = next(line for line in src.splitlines() if '"filed_date"' in line)
    generated = set(re.findall(r'"(\w+)"', claims_line.split("rng.choice")[1].split("]")[0]))
    assert q.ALLOWED_STATUS == generated
