terraform {
  required_providers {
    snowflake = { source = "snowflakedb/snowflake" }
  }
}

resource "snowflake_database" "layer" {
  for_each                    = toset(var.layers)
  name                        = each.value
  data_retention_time_in_days = 1 # keep Time Travel short on a trial to save storage
}

# Managed-access schemas: only the schema owner role can grant privileges on objects inside.
resource "snowflake_schema" "domain" {
  for_each            = { for pair in setproduct(var.layers, var.domains) : "${pair[0]}.${pair[1]}" => pair }
  database            = snowflake_database.layer[each.value[0]].name
  name                = each.value[1]
  with_managed_access = "true"
}

locals {
  # key: "HANBIT_RAW.CLAIMS" => { db, schema, role_prefix = "RAW_CLAIMS" }
  schemas = {
    for k, pair in { for p in setproduct(var.layers, var.domains) : "${p[0]}.${p[1]}" => p } :
    k => { db = pair[0], schema = pair[1], role_prefix = "${var.layer_prefix[pair[0]]}_${pair[1]}" }
  }
}

resource "snowflake_account_role" "access_ro" {
  for_each = local.schemas
  name     = "${each.value.role_prefix}_RO"
  comment  = "Access role: read ${each.key}"
}

resource "snowflake_account_role" "access_rw" {
  for_each = local.schemas
  name     = "${each.value.role_prefix}_RW"
  comment  = "Access role: read/write ${each.key}"
}

# RW inherits RO
resource "snowflake_grant_account_role" "rw_includes_ro" {
  for_each         = local.schemas
  role_name        = snowflake_account_role.access_ro[each.key].name
  parent_role_name = snowflake_account_role.access_rw[each.key].name
}

resource "snowflake_grant_privileges_to_account_role" "db_usage" {
  for_each          = local.schemas
  account_role_name = snowflake_account_role.access_ro[each.key].name
  privileges        = ["USAGE"]
  on_account_object {
    object_type = "DATABASE"
    object_name = each.value.db
  }
  depends_on = [snowflake_schema.domain]
}

resource "snowflake_grant_privileges_to_account_role" "schema_usage" {
  for_each          = local.schemas
  account_role_name = snowflake_account_role.access_ro[each.key].name
  privileges        = ["USAGE"]
  on_schema {
    schema_name = "\"${each.value.db}\".\"${each.value.schema}\""
  }
  depends_on = [snowflake_schema.domain]
}

resource "snowflake_grant_privileges_to_account_role" "ro_future" {
  for_each          = { for pair in setproduct(keys(local.schemas), ["TABLES", "VIEWS", "DYNAMIC TABLES"]) : "${pair[0]}|${pair[1]}" => pair }
  account_role_name = snowflake_account_role.access_ro[each.value[0]].name
  privileges        = ["SELECT"]
  on_schema_object {
    future {
      object_type_plural = each.value[1]
      in_schema          = "\"${local.schemas[each.value[0]].db}\".\"${local.schemas[each.value[0]].schema}\""
    }
  }
  depends_on = [snowflake_schema.domain]
}

resource "snowflake_grant_privileges_to_account_role" "rw_future" {
  for_each          = local.schemas
  account_role_name = snowflake_account_role.access_rw[each.key].name
  privileges        = ["INSERT", "UPDATE", "DELETE", "TRUNCATE"]
  on_schema_object {
    future {
      object_type_plural = "TABLES"
      in_schema          = "\"${each.value.db}\".\"${each.value.schema}\""
    }
  }
  depends_on = [snowflake_schema.domain]
}
