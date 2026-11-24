output "schema_fqns" {
  value = [for s in snowflake_schema.domain : "${s.database}.${s.name}"]
}

output "access_role_names" {
  value = concat([for r in snowflake_account_role.access_ro : r.name], [for r in snowflake_account_role.access_rw : r.name])
}
