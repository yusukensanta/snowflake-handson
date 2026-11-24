# 02 · RBAC and Terraform

**Japanese version:** [../ja/guides/02-rbac-and-terraform.md](../ja/guides/02-rbac-and-terraform.md)

## 1. Run Terraform as the service identity
```bash
export PRIVATE_KEY_PASSPHRASE='...'          # typed in your shell, never written to a file
terraform -chdir=terraform/envs/handson init
terraform -chdir=terraform/envs/handson plan  # warehouses (XS, auto-suspend 60 s), 9 persona roles, 4 monitors
terraform -chdir=terraform/envs/handson apply
terraform -chdir=terraform/envs/handson plan  # must say: No changes
```
The provider is pinned in `versions.tf` (`2.23.0`); resource names were read from the provider schema, not guessed. Aggregation policies, budgets and data metric function attachments have no resource, so they are applied from `sql/`.

## 2. The RBAC pattern
- **Object ownership** stays with Terraform's role; humans never own objects.
- **Access roles** (`<DOMAIN>_RO`, `<DOMAIN>_RW`) hold privileges on schemas; **functional roles** (personas) are granted access roles. Users get functional roles only.
- Managed-access schemas, so only the schema owner role grants privileges.
- Cloud mapping: access roles ≈ IAM policies, functional roles ≈ IAM roles/groups, `TF_ADMIN` ≈ a CI deployment role.

## Cost of this step
About 1 credit for the verification queries.

## Verify
Second `terraform plan` prints `No changes`.

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
After step 4: `No changes. Your infrastructure matches the configuration.`

## 4. Databases, access roles, personas and tags
After `apply`, Terraform has created: `HANBIT_RAW/CURATED/MARTS/GOV`, 36 access roles (`RAW_CLAIMS_RO`, `CURATED_LENDING_RW`, ...), the nine persona roles with their access-role grants and warehouse `USAGE`, and the `SENSITIVITY` tag in `HANBIT_GOV.TAGS`.

Column tags are applied in guide 04, after the CURATED tables exist (applying them earlier fails on missing columns).
To test personas, put `grant_personas_to_user = "<your user>"` in the git-ignored `terraform.tfvars`; you can then `USE ROLE CLAIMS_ADJUSTER` etc. in Snowsight.

Design rules enforced here: no direct grants to users except persona roles; `DATA_PLATFORM_ENGINEER` has RW on RAW/CURATED but (after guide 04) sees masked PII; `AUDITOR` and `SECURITY_ADMIN_FN` hold no data roles at all.

Cloud mapping: tag + masking policy ≈ Lake Formation LF-Tags or BigQuery policy tags with column-level security.
