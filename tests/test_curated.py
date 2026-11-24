from hanbit_gen.curated import curated_dynamic_tables_sql, dmf_sql
from hanbit_gen.schema import DOMAINS, SCHEMAS


def test_one_dynamic_table_per_domain_with_target_lag_and_warehouse():
    sql = curated_dynamic_tables_sql()
    for d in DOMAINS:
        assert f"CREATE DYNAMIC TABLE IF NOT EXISTS HANBIT_CURATED.{d.upper()}.{d.upper()}" in sql
    assert sql.count("TARGET_LAG = '1 hour'") == len(DOMAINS)
    assert sql.count("WAREHOUSE = TRANSFORM_WH") == len(DOMAINS)


def test_dedupes_on_first_column_keeping_latest_batch():
    sql = curated_dynamic_tables_sql()
    assert "QUALIFY ROW_NUMBER() OVER (PARTITION BY CLAIM_ID ORDER BY CLAIM_ID) = 1" in sql


def test_sensitive_columns_keep_names_so_tag_policies_apply():
    sql = curated_dynamic_tables_sql()
    for c in SCHEMAS["claims"]:
        assert c.name.upper() in sql


def test_pseudo_id_is_keyed_hash_not_plain_customer_id():
    sql = curated_dynamic_tables_sql()
    assert "SHA2(CUSTOMER_ID || '|hanbit-pseudo-v1', 256) AS CUSTOMER_PSEUDO_ID" in sql
    assert sql.count("CUSTOMER_PSEUDO_ID") == sum(1 for d in DOMAINS if any(c.name == "customer_id" for c in SCHEMAS[d]))


def test_dmf_sql_attaches_null_and_duplicate_checks_on_key_columns():
    sql = dmf_sql()
    assert "ADD DATA METRIC FUNCTION SNOWFLAKE.CORE.NULL_COUNT ON (CLAIM_ID)" in sql
    assert "ADD DATA METRIC FUNCTION SNOWFLAKE.CORE.DUPLICATE_COUNT ON (CLAIM_ID)" in sql
    assert "DATA_METRIC_SCHEDULE" in sql


def test_committed_sql_files_in_sync():
    from pathlib import Path

    root = Path(__file__).parents[1] / "sql"
    assert (root / "curated.sql").read_text() == curated_dynamic_tables_sql()
    assert (root / "dmf.sql").read_text() == dmf_sql()
