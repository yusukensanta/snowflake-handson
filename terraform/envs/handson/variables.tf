variable "snowflake_profile" {
  description = "Provider profile in ~/.snowflake/config (a different file and schema from the CLI's connections.toml). Empty = use SNOWFLAKE_* env vars: `source scripts/tf-env` locally, secrets in CI."
  type        = string
  default     = ""
}

variable "snowflake_warehouse" {
  description = "Warehouse for the provider session (tag and policy reads need one). It is created by this configuration, so on a brand-new account the first apply may need `-var snowflake_warehouse=` (empty), then a second apply."
  type        = string
  default     = "TRANSFORM_WH"
}

variable "preview_features" {
  description = "Provider preview features to enable (provider 2.23.0). Only features still in preview belong here: already-promoted ones (authentication/session policy, stage_internal, file_format_csv, auth policy attachments) warn if listed. Add e.g. snowflake_iceberg_table_resource for guide 05."
  type        = list(string)
  default = [
    "snowflake_alert_resource",
    "snowflake_email_notification_integration_resource",
    "snowflake_network_policy_attachment_resource",
    "snowflake_projection_policy_resource",
    "snowflake_table_resource",
  ]
}

variable "grant_personas_to_user" {
  description = "Your Snowflake user name, to test personas with USE ROLE. Keep in the git-ignored terraform.tfvars."
  type        = string
  default     = ""
}

variable "column_sensitivity" {
  description = "Loaded from tags.auto.tfvars.json produced by scripts/gen-data --emit-tag-map."
  type        = map(string)
  default     = {}
}

variable "apply_column_tags" {
  description = "Set true only after scripts/load-batch created the RAW tables."
  type        = bool
  default     = false
}

variable "allowed_ips" {
  description = "Your public IP as CIDR, e.g. [\"203.0.113.7/32\"]. Git-ignored terraform.tfvars only."
  type        = list(string)
  default     = []
}

variable "enforce_account_policies" {
  description = "Attach network and human auth/session policies to the account. Verify IP and MFA first."
  type        = bool
  default     = false
}

variable "alert_email" {
  description = "Verified email for alerts; empty disables alerts."
  type        = string
  default     = ""
}
