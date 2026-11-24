variable "domains" {
  description = "Business domains; one schema per domain in every layer."
  type        = list(string)
  default     = ["UNDERWRITING", "CLAIMS", "LENDING", "FINANCE", "RISK_FRAUD", "MARKETING"]
}

variable "layers" {
  description = "Database per layer."
  type        = list(string)
  default     = ["HANBIT_RAW", "HANBIT_CURATED", "HANBIT_MARTS"]
}

variable "layer_prefix" {
  description = "Short prefix used in access-role names per layer database."
  type        = map(string)
  default = {
    HANBIT_RAW     = "RAW"
    HANBIT_CURATED = "CURATED"
    HANBIT_MARTS   = "MARTS"
  }
}
