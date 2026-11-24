# Appendix · Your own S3 bucket for Iceberg (optional)

<!-- nav:top -->
[🏠 7-day map](../../README.md#7-day-map) · ← [08 CI & apply](08-ci-and-apply.md)
<!-- /nav:top -->

**Japanese version:** [../ja/guides/appendix-aws.md](../ja/guides/appendix-aws.md)

The core path needs no AWS account (Snowflake-managed storage). Use this appendix only if you own an AWS account and want the Iceberg data in **your** bucket. The repo owner has not applied it; it is `terraform validate`-checked only, so expect to adjust.

1. Review `terraform/modules/aws_appendix/main.tf`: private bucket (public access blocked, KMS encryption), an IAM role trusted by Snowflake with an **external ID** (blocks the confused-deputy problem), least-privilege S3 access.
2. Apply with the two trust variables empty, then read Snowflake's IAM user ARN and external ID from `DESC EXTERNAL VOLUME HANBIT_LAKE_VOL`.
3. Set `snowflake_iam_user_arn` and `snowflake_external_id` (in a git-ignored tfvars) and apply again.
4. Create the Iceberg table with `EXTERNAL_VOLUME = 'HANBIT_LAKE_VOL'` instead of the default storage.

Never commit your account id, role ARNs with real ids, or tfvars.

## Cost of this step
Snowflake side: about the same as guide 05. AWS side: S3 storage and requests, a few cents for this data.

## Verify
`DESC EXTERNAL VOLUME HANBIT_LAKE_VOL` succeeds and a test table writes Parquet files to the bucket.

---
<!-- nav:bottom -->
[🏠 7-day map](../../README.md#7-day-map) · ← [08 CI & apply](08-ci-and-apply.md)
<!-- /nav:bottom -->
