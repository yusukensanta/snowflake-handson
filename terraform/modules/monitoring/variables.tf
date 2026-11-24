variable "alert_email" {
  description = "Verified Snowflake user email for alerts. Empty = no alerts/integration. Keep in git-ignored terraform.tfvars."
  type        = string
  default     = ""
}

variable "warehouse" {
  type    = string
  default = "MONITOR_WH"
}

variable "monthly_credit_alert_threshold" {
  type    = number
  default = 60
}
