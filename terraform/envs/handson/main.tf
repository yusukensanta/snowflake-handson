# Credentials come from SNOWFLAKE_* env vars: `source scripts/tf-env` locally (reads the CLI profile "handson_tf"), secrets in CI.
# Nothing secret here. The provider does not read connections.toml itself.
provider "snowflake" {
  profile                  = var.snowflake_profile == "" ? null : var.snowflake_profile # "" in CI: env vars are used
  preview_features_enabled = var.preview_features
  # Tag and policy reads need an active warehouse. Set here, not only via SNOWFLAKE_WAREHOUSE, so a stale shell and CI behave the same.
  warehouse = var.snowflake_warehouse == "" ? null : var.snowflake_warehouse
}

# Warehouse => resource monitor name. The monitors are created by scripts/bootstrap and attached by scripts/attach-monitors,
# because only ACCOUNTADMIN can do either. Keep in sync with WAREHOUSE_MONITORS in scripts/lib/common.sh.
locals {
  warehouse_monitors = { for w in ["LOAD_WH", "TRANSFORM_WH", "BI_WH", "MONITOR_WH"] : w => "${w}_MONITOR" }
}

module "bootstrap" {
  source                 = "../../modules/bootstrap"
  warehouse_monitors     = local.warehouse_monitors
  grant_personas_to_user = var.grant_personas_to_user
  depends_on             = [module.databases]
}

module "governance" {
  source             = "../../modules/governance"
  column_sensitivity = var.column_sensitivity
  apply_column_tags  = var.apply_column_tags

  allowed_ips              = var.allowed_ips
  enforce_account_policies = var.enforce_account_policies
}

module "monitoring" {
  source      = "../../modules/monitoring"
  alert_email = var.alert_email
  depends_on  = [module.bootstrap]
}

module "databases" {
  source = "../../modules/databases"
}

module "ingestion" {
  source     = "../../modules/ingestion"
  depends_on = [module.databases]
}
