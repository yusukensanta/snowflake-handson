variable "warehouse_monitors" {
  description = "Warehouse name => resource monitor name. Only the keys create warehouses; monitors are attached by scripts/attach-monitors."
  type        = map(string)
}

variable "personas" {
  description = "Functional roles for the nine personas (spec section 6)."
  type        = list(string)
  default = [
    "CLAIMS_ADJUSTER", "UNDERWRITER", "LOAN_OFFICER", "FRAUD_ANALYST", "FINANCE_CONTROLLER",
    "MARKETING_ANALYST", "AUDITOR", "DATA_PLATFORM_ENGINEER", "SECURITY_ADMIN_FN",
  ]
}

variable "persona_grants" {
  description = "Persona (functional role) => access roles it receives. Users get personas only, never access roles."
  type        = map(list(string))
  default = {
    CLAIMS_ADJUSTER        = ["CURATED_CLAIMS_RO", "MARTS_CLAIMS_RO"]
    UNDERWRITER            = ["CURATED_UNDERWRITING_RO", "MARTS_UNDERWRITING_RO"]
    LOAN_OFFICER           = ["CURATED_LENDING_RO", "MARTS_LENDING_RO"]
    FRAUD_ANALYST          = ["CURATED_RISK_FRAUD_RO", "MARTS_CLAIMS_RO", "MARTS_LENDING_RO", "MARTS_UNDERWRITING_RO"]
    FINANCE_CONTROLLER     = ["CURATED_FINANCE_RO", "MARTS_FINANCE_RO", "MARTS_CLAIMS_RO"]
    MARKETING_ANALYST      = ["CURATED_MARKETING_RO", "MARTS_MARKETING_RO"]
    AUDITOR                = []
    DATA_PLATFORM_ENGINEER = ["RAW_UNDERWRITING_RW", "RAW_CLAIMS_RW", "RAW_LENDING_RW", "RAW_FINANCE_RW", "RAW_RISK_FRAUD_RW", "RAW_MARKETING_RW", "CURATED_UNDERWRITING_RW", "CURATED_CLAIMS_RW", "CURATED_LENDING_RW", "CURATED_FINANCE_RW", "CURATED_RISK_FRAUD_RW", "CURATED_MARKETING_RW"]
    SECURITY_ADMIN_FN      = []
  }
}

variable "persona_warehouses" {
  description = "Persona => warehouses it may USE."
  type        = map(list(string))
  default = {
    CLAIMS_ADJUSTER        = ["BI_WH"]
    UNDERWRITER            = ["BI_WH"]
    LOAN_OFFICER           = ["BI_WH"]
    FRAUD_ANALYST          = ["BI_WH"]
    FINANCE_CONTROLLER     = ["BI_WH"]
    MARKETING_ANALYST      = ["BI_WH"]
    AUDITOR                = ["MONITOR_WH"]
    DATA_PLATFORM_ENGINEER = ["LOAD_WH", "TRANSFORM_WH"]
    SECURITY_ADMIN_FN      = ["MONITOR_WH"]
  }
}

variable "grant_personas_to_user" {
  description = "Your own Snowflake user name, so you can USE ROLE each persona to test access. Not committed."
  type        = string
  default     = ""
}
