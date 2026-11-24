terraform {
  required_providers {
    snowflake = { source = "snowflakedb/snowflake" }
  }
}

# One monitor per warehouse; the account-level monitor is created by scripts/bootstrap.
resource "snowflake_resource_monitor" "warehouse" {
  for_each        = var.warehouse_credit_quota
  name            = "${each.key}_MONITOR"
  credit_quota    = each.value
  frequency       = "MONTHLY"
  start_timestamp = "IMMEDIATELY"

  notify_triggers           = [75, 90]
  suspend_trigger           = 100
  suspend_immediate_trigger = 110
}
