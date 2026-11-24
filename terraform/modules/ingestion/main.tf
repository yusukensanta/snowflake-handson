terraform {
  required_providers {
    snowflake = { source = "snowflakedb/snowflake" }
  }
}

resource "snowflake_file_format_csv" "gz_csv" {
  for_each                     = toset(var.domains)
  database                     = var.raw_database
  schema                       = each.value
  name                         = "CSV_GZ"
  skip_header                  = 1
  compression                  = "GZIP"
  field_optionally_enclosed_by = "\""
}

# Internal named stage: encrypted by Snowflake (server-side), no AWS account needed.
resource "snowflake_stage_internal" "landing" {
  for_each = toset(var.domains)
  database = var.raw_database
  schema   = each.value
  name     = "LANDING"
  encryption {
    snowflake_sse {}
  }
  depends_on = [snowflake_file_format_csv.gz_csv]
}
