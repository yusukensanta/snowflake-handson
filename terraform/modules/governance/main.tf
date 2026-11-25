terraform {
  required_providers {
    snowflake = { source = "snowflakedb/snowflake" }
  }
}

resource "snowflake_database" "gov" {
  name                        = "HANBIT_GOV"
  data_retention_time_in_days = 1
}

resource "snowflake_schema" "tags" {
  database = snowflake_database.gov.name
  name     = "TAGS"
}

resource "snowflake_schema" "policies" {
  database = snowflake_database.gov.name
  name     = "POLICIES"
}

resource "snowflake_schema" "entitlements" {
  database = snowflake_database.gov.name
  name     = "ENTITLEMENTS"
}

resource "snowflake_tag" "sensitivity" {
  database               = snowflake_database.gov.name
  schema                 = snowflake_schema.tags.name
  name                   = "SENSITIVITY"
  ordered_allowed_values = ["PII", "HEALTH", "CREDIT", "FINANCIAL"]
  comment                = "Data sensitivity class; masking policies attach to this tag"

  # The masking policies are attached by snowflake_execute.tag_masking below. The tag resource reads them back from Snowflake,
  # and without this a plan shows them as removed; applying that plan would unset the masking.
  lifecycle {
    ignore_changes = [masking_policies]
  }
}

locals {
  tag_targets = var.apply_column_tags ? {
    for pair in setproduct(var.tag_layers, keys(var.column_sensitivity)) :
    "${pair[0]}.${pair[1]}" => {
      column = "\"${pair[0]}\".\"${upper(split(".", pair[1])[0])}\".\"${upper(split(".", pair[1])[0])}\".\"${upper(split(".", pair[1])[1])}\""
      value  = upper(var.column_sensitivity[pair[1]])
    }
  } : {}
}

resource "snowflake_tag_association" "column" {
  for_each           = local.tag_targets
  object_identifiers = [each.value.column]
  object_type        = "COLUMN"
  tag_id             = snowflake_tag.sensitivity.fully_qualified_name
  tag_value          = each.value.value
}

# ---- Tag-based masking: one policy per data type; the logic branches on the tag value. ----
resource "snowflake_masking_policy" "sensitive_string" {
  database = snowflake_database.gov.name
  schema   = snowflake_schema.policies.name
  name     = "MASK_SENSITIVE_STRING"
  argument {
    name = "VAL"
    type = "VARCHAR"
  }
  return_data_type = "VARCHAR"
  body             = <<-EOT
    CASE SYSTEM$GET_TAG_ON_CURRENT_COLUMN('HANBIT_GOV.TAGS.SENSITIVITY')
      WHEN 'PII' THEN CASE
        WHEN IS_ROLE_IN_SESSION('UNDERWRITER') OR IS_ROLE_IN_SESSION('LOAN_OFFICER') THEN VAL
        WHEN IS_ROLE_IN_SESSION('FRAUD_ANALYST') THEN SHA2(VAL, 256)
        ELSE '***MASKED***' END
      WHEN 'HEALTH' THEN CASE
        WHEN IS_ROLE_IN_SESSION('CLAIMS_ADJUSTER') THEN VAL
        ELSE '***MASKED***' END
      ELSE '***MASKED***'
    END
  EOT
}

resource "snowflake_masking_policy" "sensitive_number" {
  database = snowflake_database.gov.name
  schema   = snowflake_schema.policies.name
  name     = "MASK_SENSITIVE_NUMBER"
  argument {
    name = "VAL"
    type = "NUMBER"
  }
  return_data_type = "NUMBER"
  body             = <<-EOT
    CASE SYSTEM$GET_TAG_ON_CURRENT_COLUMN('HANBIT_GOV.TAGS.SENSITIVITY')
      WHEN 'CREDIT' THEN CASE WHEN IS_ROLE_IN_SESSION('LOAN_OFFICER') THEN VAL ELSE NULL END
      WHEN 'FINANCIAL' THEN CASE WHEN IS_ROLE_IN_SESSION('FINANCE_CONTROLLER') THEN VAL ELSE NULL END
      ELSE NULL
    END
  EOT
}

resource "snowflake_execute" "tag_masking" {
  execute = "ALTER TAG HANBIT_GOV.TAGS.SENSITIVITY SET MASKING POLICY HANBIT_GOV.POLICIES.MASK_SENSITIVE_STRING, MASKING POLICY HANBIT_GOV.POLICIES.MASK_SENSITIVE_NUMBER"
  revert  = "ALTER TAG HANBIT_GOV.TAGS.SENSITIVITY UNSET MASKING POLICY HANBIT_GOV.POLICIES.MASK_SENSITIVE_STRING, MASKING POLICY HANBIT_GOV.POLICIES.MASK_SENSITIVE_NUMBER"
  depends_on = [
    snowflake_masking_policy.sensitive_string,
    snowflake_masking_policy.sensitive_number,
    snowflake_tag.sensitivity,
  ]
}

# ---- Row access: data-driven. The table must exist before the policy (Snowflake validates the policy body when it
# is created); sql/policies_attach.sql fills it with rows. ----
resource "snowflake_table" "role_region" {
  database = snowflake_database.gov.name
  schema   = snowflake_schema.entitlements.name
  name     = "ROLE_REGION"
  comment  = "Entitlements as data: which role sees which region (RAP_REGION)"
  column {
    name = "ROLE_NAME"
    type = "VARCHAR"
  }
  column {
    name = "REGION"
    type = "VARCHAR"
  }
}

resource "snowflake_row_access_policy" "region" {
  depends_on = [snowflake_table.role_region]
  database   = snowflake_database.gov.name
  schema     = snowflake_schema.policies.name
  name       = "RAP_REGION"
  argument {
    name = "ROW_REGION"
    type = "VARCHAR"
  }
  # TF_ADMIN is the build/owner role (CTAS to Iceberg, Dynamic Table owner); no human persona maps to it.
  body = <<-EOT
    IS_ROLE_IN_SESSION('DATA_PLATFORM_ENGINEER') OR IS_ROLE_IN_SESSION('TF_ADMIN')
    OR EXISTS (
      SELECT 1 FROM HANBIT_GOV.ENTITLEMENTS.ROLE_REGION e
      WHERE e.ROLE_NAME = CURRENT_ROLE() AND (e.REGION = ROW_REGION OR e.REGION = '*')
    )
  EOT
}

# ---- Projection: identifier usable in joins/filters but never selectable by marketing. ----
resource "snowflake_projection_policy" "id_joinable" {
  database = snowflake_database.gov.name
  schema   = snowflake_schema.policies.name
  name     = "PROJ_ID_JOINABLE"
  body     = "PROJECTION_CONSTRAINT(ALLOW => NOT IS_ROLE_IN_SESSION('MARKETING_ANALYST'))"
}

# ---- Identity and network policies ----
resource "snowflake_network_policy" "handson" {
  count           = length(var.allowed_ips) > 0 ? 1 : 0
  name            = "NP_HANDSON"
  allowed_ip_list = var.allowed_ips
  comment         = "Only the owner's IP may sign in"
}

resource "snowflake_network_policy_attachment" "account" {
  count               = length(var.allowed_ips) > 0 && var.enforce_account_policies ? 1 : 0
  network_policy_name = snowflake_network_policy.handson[0].name
  set_for_account     = true
}

# Humans: MFA enrolment required. Service users: key-pair only, no password.
resource "snowflake_authentication_policy" "human" {
  database               = snowflake_database.gov.name
  schema                 = snowflake_schema.policies.name
  name                   = "AP_HUMAN"
  authentication_methods = ["ALL"]
  mfa_enrollment         = "REQUIRED"
}

resource "snowflake_authentication_policy" "service" {
  database               = snowflake_database.gov.name
  schema                 = snowflake_schema.policies.name
  name                   = "AP_SERVICE"
  authentication_methods = ["KEYPAIR"]
}

# AP_SERVICE is attached to the TERRAFORM user by sql/policies_attach.sql (scripts/apply-policies), not here: the provider's
# user attachment resource reads the reference back as TF_ADMIN, finds nothing, and fails with "Root object was present, but now absent".

resource "snowflake_account_authentication_policy_attachment" "human" {
  count                 = var.enforce_account_policies ? 1 : 0
  authentication_policy = snowflake_authentication_policy.human.fully_qualified_name
}

resource "snowflake_session_policy" "human" {
  database                     = snowflake_database.gov.name
  schema                       = snowflake_schema.policies.name
  name                         = "SP_HUMAN"
  session_idle_timeout_mins    = 30
  session_ui_idle_timeout_mins = 30
}
