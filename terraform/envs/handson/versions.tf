terraform {
  required_version = ">= 1.9"
  required_providers {
    snowflake = {
      source  = "snowflakedb/snowflake"
      version = "2.23.0" # latest 2.24.0 was <2 days old at pin time; bump after reading release notes
    }
  }
}
