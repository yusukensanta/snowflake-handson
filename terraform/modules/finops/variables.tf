variable "warehouse_credit_quota" {
  description = "Monthly credit quota per warehouse monitor (from guide 00 budget table)."
  type        = map(number)
  default = {
    LOAD_WH      = 10
    TRANSFORM_WH = 10
    BI_WH        = 10
    MONITOR_WH   = 5
  }
}
