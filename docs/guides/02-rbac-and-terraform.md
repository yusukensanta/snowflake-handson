# 02 · RBAC and Terraform

<!-- nav:top -->
[🏠 7-day map](../../README.md#7-day-map) · ← [01 Setup](01-setup-and-guardrails.md) · [03 Ingestion](03-ingestion.md) →
<!-- /nav:top -->

**Japanese version:** [../ja/guides/02-rbac-and-terraform.md](../ja/guides/02-rbac-and-terraform.md)

## 1. Run Terraform as the service identity
```bash
export PRIVATE_KEY_PASSPHRASE='...'          # typed in your shell, never written to a file
source scripts/tf-env                         # exports SNOWFLAKE_* for the provider from the [handson_tf] profile
terraform -chdir=terraform/envs/handson init
terraform -chdir=terraform/envs/handson plan  # warehouses (XS, auto-suspend 60 s), 9 persona roles
terraform -chdir=terraform/envs/handson apply
terraform -chdir=terraform/envs/handson plan  # must say: No changes
scripts/attach-monitors --execute             # admin connection: attach the per-warehouse resource monitors
```
The monitors were created by `scripts/bootstrap` (guide 01). Only `ACCOUNTADMIN` can assign a warehouse to a resource monitor, so this step is outside Terraform, which ignores the warehouses' `resource_monitor` setting. It is idempotent: re-run it (with `--execute`) after any `terraform apply` that creates a warehouse (including the CI apply in guide 08).
The Terraform provider does not read `connections.toml` (that is the CLI's file), so `scripts/tf-env` translates the profile into the `SNOWFLAKE_*` variables the provider and CI use. Source it in every new terminal. The provider session uses `TRANSFORM_WH` (variable `snowflake_warehouse`) for tag and policy reads. If that warehouse does not exist yet (a brand-new account), create the warehouses first with `terraform apply -target=module.bootstrap.snowflake_warehouse.this`, then run the full `apply`. The provider is pinned in `versions.tf` (`2.23.0`); resource names were read from the provider schema, not guessed. Aggregation policies, budgets and data metric function attachments have no resource, so they are applied from `sql/`.

## 2. The RBAC pattern
- **Object ownership** stays with Terraform's role; humans never own objects.
- **Access roles** (`<DOMAIN>_RO`, `<DOMAIN>_RW`) hold privileges on schemas; **functional roles** (personas) are granted access roles. Users get functional roles only.
- Managed-access schemas, so only the schema owner role grants privileges.
- Cloud mapping: access roles ≈ IAM policies, functional roles ≈ IAM roles/groups, `TF_ADMIN` ≈ a CI deployment role.

## Cost of this step
About 1 credit for the verification queries.

## Verify

```bash
terraform -chdir=terraform/envs/handson plan   # No changes. Your infrastructure matches the configuration.
scripts/attach-monitors --execute
scripts/cost-guard --status                    # each of LOAD_WH, TRANSFORM_WH, BI_WH, MONITOR_WH shows its own resource_monitor
snow sql -c handson_tf -q "SHOW ROLES LIKE 'CLAIMS_ADJUSTER'"
snow sql -c handson_tf -q "SHOW GRANTS TO ROLE CLAIMS_ADJUSTER"   # access roles and USAGE on a warehouse, no direct table grants
scripts/verify-step 02 --execute
```
Expect `[info] step 02 verified`. In Snowsight (role `TF_ADMIN`), **Admin > Warehouses** lists the four warehouses, all `Suspended` when idle. `COMPUTE_WH`, `SNOWFLAKE_LEARNING_WH` and `SYSTEM$STREAMLIT_NOTEBOOK_WH` are trial defaults with no monitor of their own; the account monitor covers them.

## 3. Import lab: adopt hand-built objects
Real teams start with click-ops. Terraform can adopt those objects without recreating them.

1. In Snowsight (role `TF_ADMIN`) create by hand:
   `CREATE ROLE LAB_IMPORT_ROLE;` and `CREATE WAREHOUSE LAB_IMPORT_WH WAREHOUSE_SIZE = XSMALL AUTO_SUSPEND = 60;`
2. Copy `terraform/envs/handson/import-lab/lab.tf.example` to `terraform/envs/handson/lab.tf`.
3. `terraform plan` shows 2 imports. If it also shows changes, your config differs from reality: fix the config, not the object.
4. `terraform apply`, then `terraform plan` again: `No changes`.
5. **Drift:** in Snowsight run `ALTER WAREHOUSE LAB_IMPORT_WH SET WAREHOUSE_SIZE = SMALL;` then `terraform plan` shows the drift and would revert it. This is how you catch out-of-band changes.
6. Clean up: delete `lab.tf` and run `terraform destroy -target=snowflake_account_role.lab -target=snowflake_warehouse.lab` before removing the file (or drop both objects in Snowsight and `terraform state rm`).

To discover attributes of an existing object, write only the `import` block and run `terraform plan -generate-config-out=generated.tf`, then review before keeping anything.

## Cost of the import lab
Under 0.1 credit (an XS warehouse that never runs queries).

## Verify (import lab)

```bash
terraform -chdir=terraform/envs/handson plan   # after step 4: No changes. Your infrastructure matches the configuration.
```
After step 5 (the drift), the same command must show `LAB_IMPORT_WH` changing `warehouse_size` back to `XSMALL`. Confirm the object in Snowflake with `snow sql -c handson_tf -q "SHOW WAREHOUSES LIKE 'LAB_IMPORT_WH'"`.

## 4. Databases, access roles, personas and tags
After `apply`, Terraform has created: `HANBIT_RAW/CURATED/MARTS/GOV`, 36 access roles (`RAW_CLAIMS_RO`, `CURATED_LENDING_RW`, ...), the nine persona roles with their access-role grants and warehouse `USAGE`, and the `SENSITIVITY` tag in `HANBIT_GOV.TAGS`.

Column tags are applied in guide 04, after the CURATED tables exist (applying them earlier fails on missing columns).
To test personas, put `grant_personas_to_user = "<your user>"` in the git-ignored `terraform.tfvars`; you can then `USE ROLE CLAIMS_ADJUSTER` etc. in Snowsight.

Design rules enforced here: no direct grants to users except persona roles; `DATA_PLATFORM_ENGINEER` has RW on RAW/CURATED but (after guide 04) sees masked PII; `AUDITOR` and `SECURITY_ADMIN_FN` hold no data roles at all.

Cloud mapping: tag + masking policy ≈ Lake Formation LF-Tags or BigQuery policy tags with column-level security.

---
<!-- nav:bottom -->
[🏠 7-day map](../../README.md#7-day-map) · ← [01 Setup](01-setup-and-guardrails.md) · [03 Ingestion](03-ingestion.md) →
<!-- /nav:bottom -->
