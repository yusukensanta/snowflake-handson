# 05 · Transform and Iceberg

<!-- nav:top -->
[🏠 7-day map](../../README.md#7-day-map) · ← [03 Ingestion](03-ingestion.md) · [04 Governance](04-governance.md) →
<!-- /nav:top -->

**Japanese version:** [../ja/guides/05-transform-and-iceberg.md](../ja/guides/05-transform-and-iceberg.md)

## 1. Transform with Dynamic Tables (do this before guide 04)
A **Dynamic Table** is a declarative query Snowflake keeps fresh within a `TARGET_LAG`. You describe the result; Snowflake schedules incremental refreshes. Cloud analogue: a materialized view with a freshness SLA, or a dbt model plus its scheduler, in one object.

```bash
scripts/gen-data --emit-curated sql/curated.sql   # already committed; regenerates from the one schema definition
scripts/apply-curated --dry-run
scripts/apply-curated                              # 6 Dynamic Tables in HANBIT_CURATED + data metric functions
```
What the curated layer does: deduplicates on the business key, keeps the column names (so tag-based masking applies unchanged), and adds `CUSTOMER_PSEUDO_ID = SHA2(customer_id || salt)` so fraud and marketing can join without raw identifiers.

**Why `IF NOT EXISTS`:** `CREATE OR REPLACE` would silently drop the masking/row policies attached to the table. If you change a definition, drop that table deliberately, recreate, then re-run `scripts/apply-policies`.

**Lag versus cost:** `TARGET_LAG = '1 hour'` keeps refreshes rare. A 1-minute lag would keep `TRANSFORM_WH` awake and cost many times more. Measure: after one day compare `V_CREDITS_BY_WAREHOUSE` for `TRANSFORM_WH`. Suspend when idle:
```bash
scripts/cost-guard --suspend-all     # suspends warehouses and Dynamic Tables
```
**Data quality:** `sql/dmf.sql` attaches `NULL_COUNT` and `DUPLICATE_COUNT` data metric functions (hourly) to each key column; results appear in `SNOWFLAKE.LOCAL.DATA_QUALITY_MONITORING_RESULTS`.

## Cost of this step (transform)
About 8 credits, mostly the first full refresh of 1.2 million rows on XS.

## Verify (transform)
`SELECT COUNT(*) FROM HANBIT_CURATED.CLAIMS.CLAIMS` equals the RAW count; `SHOW DYNAMIC TABLES IN DATABASE HANBIT_CURATED` shows `scheduling_state = ACTIVE`.

## 2. Iceberg v3 on Snowflake-managed storage
Apache Iceberg is an open table format: data is Parquet files plus metadata that any engine can read. With **Snowflake as the catalog and Snowflake-managed storage** you get an open-format table without owning an S3 bucket or IAM role (the AWS-bucket variant is in the appendix and is never applied by the repo owner). Cloud analogue: a Glue/Hive-style Iceberg table, minus the storage plumbing.

```bash
snow sql -c handson_tf -f sql/iceberg.sql      # creates HANBIT_MARTS.LAKE.CLAIMS_FACT (ICEBERG_VERSION = 3)
```
- `ICEBERG_VERSION` is fixed at creation (`ALTER` cannot change it). The default is v2; this lab sets v3 explicitly. Check with `SHOW PARAMETERS LIKE 'ICEBERG_VERSION' IN TABLE ...`.
- The table holds only pseudonymised, non-sensitive columns. **External engines are outside your masking and row policies unless they connect through the Horizon catalog**, so never publish raw PII in an open table. This is the main governance lesson of this section.

### Read it from outside Snowflake
Create a programmatic access token for a least-privilege user/role, export it (never commit it), then:
```bash
export SNOWFLAKE_ACCOUNT_URL="https://<your-account>.snowflakecomputing.com"
export SNOWFLAKE_PAT="<token>"
scripts/open-read          # PyIceberg through the Horizon Iceberg REST catalog
```

### Fallback
Snowflake-managed Iceberg storage or v3 may not be enabled in ap-northeast-2 for your trial; `scripts/preflight` probes this. If `sql/iceberg.sql` fails, read the section as concept only, record the error in your notes, and continue: nothing later depends on it.

## Cost of this step (Iceberg)
About 1 credit (one CTAS on XS plus storage).

## Verify (Iceberg)
`SELECT COUNT(*) FROM HANBIT_MARTS.LAKE.CLAIMS_FACT` equals the curated claims count; the `ICEBERG_VERSION` parameter shows `3`.

---
<!-- nav:bottom -->
[🏠 7-day map](../../README.md#7-day-map) · ← [03 Ingestion](03-ingestion.md) · [04 Governance](04-governance.md) →
<!-- /nav:bottom -->
