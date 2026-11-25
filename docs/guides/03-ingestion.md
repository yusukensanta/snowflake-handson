# 03 · Ingestion

<!-- nav:top -->
[🏠 7-day map](../../README.md#7-day-map) · ← [02 RBAC & Terraform](02-rbac-and-terraform.md) · [05 Transform & Iceberg](05-transform-and-iceberg.md) →
<!-- /nav:top -->

**Japanese version:** [../ja/guides/03-ingestion.md](../ja/guides/03-ingestion.md)

You need no AWS account: files go to a Snowflake **internal stage** (encrypted by Snowflake), and rows can also be pushed with **Snowpipe Streaming**.

| Path | When | Cloud analogue |
|---|---|---|
| `PUT` + `COPY INTO` (batch) | Files you already have | `aws s3 cp` + a Redshift `COPY`, or a BigQuery load job |
| Snowpipe Streaming (rows) | Event/row producers, low latency | Kinesis Firehose / BigQuery Storage Write API |
| (Appendix) S3 + Snowpipe auto-ingest | You own an AWS account | S3 event → SQS → loader |

## 1. Generate synthetic data
```bash
scripts/gen-data                 # 200,000 rows x 6 domains → data/out/*.csv.gz (about 21 MB compressed, 85 MB raw)
scripts/gen-data --rows 1000     # tiny run while you learn
```
Same seed ⇒ identical bytes. National-ID-like numbers have an invalid check digit by design.

## 2. Create schemas, stages and file formats (Terraform)
`terraform -chdir=terraform/envs/handson apply` creates `HANBIT_RAW/CURATED/MARTS`, one managed-access schema per domain, a `LANDING` internal stage and a `CSV_GZ` file format per RAW schema.

## 3. Batch load
```bash
scripts/load-batch --dry-run
scripts/load-batch               # run as the TERRAFORM identity until guide 02's roles are granted
scripts/load-batch               # again: loads 0 new rows (COPY remembers loaded files)
```
`sql/raw_tables.sql` is generated from the single schema definition (`scripts/gen-data --emit-ddl sql/raw_tables.sql`); a test fails if they drift.

## 4. Streaming load
```bash
scripts/stream-load --domain claims --file data/out/claims.csv.gz
```
Rows land in `HANBIT_RAW.CLAIMS.CLAIMS_STREAM` through the high-performance SDK (key-pair auth, offset tokens per batch). **Unverified on a live account:** the SDK's connection `properties` keys; if the call fails, compare with the SDK reference and adjust `SdkSink` in `src/sfops/streaming.py`.

## Cost of this step
About 8 credits (XS `LOAD_WH`, auto-suspend 60 s). Streaming is billed per ingested volume, not warehouse time.

## Verify
`SELECT COUNT(*) FROM HANBIT_RAW.CLAIMS.CLAIMS` equals `--rows` (200,000 by default); the second `scripts/load-batch` loads nothing.

---
<!-- nav:bottom -->
[🏠 7-day map](../../README.md#7-day-map) · ← [02 RBAC & Terraform](02-rbac-and-terraform.md) · [05 Transform & Iceberg](05-transform-and-iceberg.md) →
<!-- /nav:bottom -->
