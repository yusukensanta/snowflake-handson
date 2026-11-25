# Credentials come from SNOWFLAKE_* env vars: `source scripts/tf-env` locally (reads the CLI profile "handson_tf"), secrets in CI.
# Nothing secret here. The provider does not read connections.toml itself.
provider "snowflake" {
  profile                  = var.snowflake_profile == "" ? null : var.snowflake_profile # "" in CI: env vars are used
  preview_features_enabled = var.preview_features
}

module "finops" {
  source = "../../modules/finops"
}

module "bootstrap" {
  source                 = "../../modules/bootstrap"
  warehouse_monitors     = module.finops.warehouse_monitor_names
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
