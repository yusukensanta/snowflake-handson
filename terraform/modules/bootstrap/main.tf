terraform {
  required_providers {
    snowflake = { source = "snowflakedb/snowflake" }
  }
}

resource "snowflake_account_role" "persona" {
  for_each = toset(var.personas)
  name     = each.value
  comment  = "Functional role (persona) - privileges come only via access roles"
}

# All warehouses: XS, auto-suspend 60 s, statement timeout. The resource monitor is attached outside Terraform
# (scripts/attach-monitors, ACCOUNTADMIN only), so Terraform must not try to manage or unset it.
resource "snowflake_warehouse" "this" {
  for_each                     = var.warehouse_monitors
  name                         = each.key
  warehouse_size               = "XSMALL"
  auto_suspend                 = 60
  auto_resume                  = "true"
  initially_suspended          = true
  statement_timeout_in_seconds = 1800
  comment                      = "Hands-on warehouse; see guide 01 for cost guardrails"

  lifecycle {
    ignore_changes = [resource_monitor]
  }
}

locals {
  persona_access = flatten([for p, roles in var.persona_grants : [for r in roles : { persona = p, access = r }]])
  persona_wh     = flatten([for p, whs in var.persona_warehouses : [for w in whs : { persona = p, wh = w }]])
}

resource "snowflake_grant_account_role" "persona_access" {
  for_each         = { for x in local.persona_access : "${x.persona}|${x.access}" => x }
  role_name        = each.value.access
  parent_role_name = snowflake_account_role.persona[each.value.persona].name
}

resource "snowflake_grant_privileges_to_account_role" "persona_wh" {
  for_each          = { for x in local.persona_wh : "${x.persona}|${x.wh}" => x }
  account_role_name = snowflake_account_role.persona[each.value.persona].name
  privileges        = ["USAGE"]
  on_account_object {
    object_type = "WAREHOUSE"
    object_name = snowflake_warehouse.this[each.value.wh].name
  }
}

resource "snowflake_grant_account_role" "persona_to_user" {
  for_each  = var.grant_personas_to_user == "" ? toset([]) : toset(var.personas)
  role_name = snowflake_account_role.persona[each.value].name
  user_name = var.grant_personas_to_user
}
