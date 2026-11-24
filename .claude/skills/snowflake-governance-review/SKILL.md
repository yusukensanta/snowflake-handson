---
name: snowflake-governance-review
description: Use when reviewing or changing masking, row access, tags, network/auth policies or roles in this repo
---
# Governance review
Check: no ACCOUNTADMIN for routine work; service users key-pair only; new sensitive columns have a SENSITIVITY tag (`src/hanbit_gen/schema.py`) and are covered by `sql/matrix/access-matrix.yaml`; policies attach to CURATED not RAW; Dynamic Tables use IF NOT EXISTS so policies survive; Iceberg tables hold no raw PII. Finish with `scripts/access-matrix --dry-run`. Report findings as a table (file, issue, severity).
