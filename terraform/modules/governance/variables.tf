variable "column_sensitivity" {
  description = "Map 'domain.column' => sensitivity (pii|health|credit|financial), from scripts/gen-data --emit-tag-map."
  type        = map(string)
  default     = {}
}

variable "tag_layers" {
  description = "Layers whose tables receive column tags. Tables must exist (run scripts/load-batch first)."
  type        = list(string)
  default     = ["HANBIT_CURATED"] # never RAW: Dynamic Tables read RAW as TF_ADMIN and would persist masked values
}

variable "apply_column_tags" {
  description = "Second-stage switch: set true once the CURATED tables exist (guide 05 section 1). Keep it in terraform.tfvars, not a one-off -var."
  type        = bool
  default     = false
}

variable "allowed_ips" {
  description = "CIDR list for the account network policy (your public IP/32). Empty = policy not created."
  type        = list(string)
  default     = []
}

variable "enforce_account_policies" {
  description = "Attach network + human authentication/session policies to the ACCOUNT. Keep false until you verified your IP and MFA enrolment, or you can lock yourself out."
  type        = bool
  default     = false
}
