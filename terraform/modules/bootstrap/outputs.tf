output "warehouse_names" {
  value = { for k, w in snowflake_warehouse.this : k => w.name }
}

output "persona_roles" {
  value = [for r in snowflake_account_role.persona : r.name]
}
