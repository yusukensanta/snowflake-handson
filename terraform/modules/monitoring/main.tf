terraform {
  required_providers {
    snowflake = { source = "snowflakedb/snowflake" }
  }
}

resource "snowflake_database" "ops" {
  name                        = "HANBIT_OPS"
  data_retention_time_in_days = 1
}

resource "snowflake_schema" "monitoring" {
  database = snowflake_database.ops.name
  name     = "MONITORING"
}

locals {
  views = {
    V_COPY_ERRORS             = "SELECT FILE_NAME, TABLE_NAME, LAST_LOAD_TIME, STATUS, ERROR_COUNT, FIRST_ERROR_MESSAGE FROM SNOWFLAKE.ACCOUNT_USAGE.COPY_HISTORY WHERE ERROR_COUNT > 0"
    V_FAILED_LOGINS           = "SELECT EVENT_TIMESTAMP, USER_NAME, CLIENT_IP, ERROR_MESSAGE FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY WHERE IS_SUCCESS = 'NO'"
    V_CREDITS_BY_SERVICE      = "SELECT DATE_TRUNC('day', START_TIME) AS DAY, SERVICE_TYPE, SUM(CREDITS_USED) AS CREDITS FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_HISTORY GROUP BY 1, 2"
    V_CREDITS_BY_WAREHOUSE    = "SELECT DATE_TRUNC('day', START_TIME) AS DAY, WAREHOUSE_NAME, SUM(CREDITS_USED) AS CREDITS FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY GROUP BY 1, 2"
    V_DYNAMIC_TABLE_REFRESHES = "SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.DYNAMIC_TABLE_REFRESH_HISTORY"
    V_TASK_RUNS               = "SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.TASK_HISTORY"
    V_PIPE_USAGE              = "SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.PIPE_USAGE_HISTORY"
  }
}

resource "snowflake_execute" "view" {
  for_each   = local.views
  execute    = "CREATE OR REPLACE VIEW HANBIT_OPS.MONITORING.${each.key} AS ${each.value}"
  revert     = "DROP VIEW IF EXISTS HANBIT_OPS.MONITORING.${each.key}"
  depends_on = [snowflake_schema.monitoring]
}

# ---- Alerts (only when an alert email is provided) ----
resource "snowflake_email_notification_integration" "alerts" {
  count              = var.alert_email == "" ? 0 : 1
  name               = "HANDSON_ALERT_EMAIL"
  enabled            = true
  allowed_recipients = [var.alert_email]
}

locals {
  alerts = var.alert_email == "" ? {} : {
    FAILED_LOGINS = {
      condition = "SELECT 1 FROM HANBIT_OPS.MONITORING.V_FAILED_LOGINS WHERE EVENT_TIMESTAMP > DATEADD('hour', -1, CURRENT_TIMESTAMP()) HAVING COUNT(*) >= 3"
      subject   = "Hands-on: 3+ failed logins in the last hour"
    }
    COPY_ERRORS = {
      condition = "SELECT 1 FROM HANBIT_OPS.MONITORING.V_COPY_ERRORS WHERE LAST_LOAD_TIME > DATEADD('hour', -1, CURRENT_TIMESTAMP()) HAVING COUNT(*) > 0"
      subject   = "Hands-on: COPY errors in the last hour"
    }
    CREDIT_BURN = {
      condition = "SELECT 1 FROM HANBIT_OPS.MONITORING.V_CREDITS_BY_SERVICE WHERE DAY >= DATE_TRUNC('month', CURRENT_DATE()) HAVING SUM(CREDITS) > ${var.monthly_credit_alert_threshold}"
      subject   = "Hands-on: monthly credits above ${var.monthly_credit_alert_threshold}"
    }
  }
}

resource "snowflake_alert" "this" {
  for_each  = local.alerts
  database  = snowflake_database.ops.name
  schema    = snowflake_schema.monitoring.name
  name      = each.key
  warehouse = var.warehouse
  alert_schedule {
    interval = 60
  }
  condition = each.value.condition
  action    = "CALL SYSTEM$SEND_EMAIL('HANDSON_ALERT_EMAIL', '${var.alert_email}', '${each.value.subject}', 'See HANBIT_OPS.MONITORING views.')"
  enabled   = true
  depends_on = [
    snowflake_execute.view,
    snowflake_email_notification_integration.alerts,
  ]
}
