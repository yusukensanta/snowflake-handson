variable "domains" {
  type    = list(string)
  default = ["UNDERWRITING", "CLAIMS", "LENDING", "FINANCE", "RISK_FRAUD", "MARKETING"]
}

variable "raw_database" {
  type    = string
  default = "HANBIT_RAW"
}
