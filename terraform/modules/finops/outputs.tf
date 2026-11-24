output "warehouse_monitor_names" {
  value = { for k, m in snowflake_resource_monitor.warehouse : k => m.name }
}
