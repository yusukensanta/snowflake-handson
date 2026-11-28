# 07 · Monitoring, FinOps and teardown

<!-- nav:top -->
[🏠 7-day map](../../README.md#7-day-map) · ← [06 BI & AI](06-bi-and-ai.md) · [08 CI & apply](08-ci-and-apply.md) →
<!-- /nav:top -->

**Japanese version:** [../ja/guides/07-monitoring-finops-teardown.md](../ja/guides/07-monitoring-finops-teardown.md)

## 1. Platform and pipeline monitoring
Terraform (`monitoring` module) creates `HANBIT_OPS.MONITORING` views over `SNOWFLAKE.ACCOUNT_USAGE`:

| View | Answers |
|---|---|
| `V_COPY_ERRORS` | Which batch loads failed, and why |
| `V_PIPE_USAGE`, `V_TASK_RUNS` | Streaming/pipe and task history |
| `V_DYNAMIC_TABLE_REFRESHES` | Refresh state and lag of curated tables |
| `V_FAILED_LOGINS` | Failed sign-ins, source IP |
| `V_CREDITS_BY_SERVICE`, `V_CREDITS_BY_WAREHOUSE` | Where credits go |

Set `alert_email` (a verified user email, in the git-ignored `terraform.tfvars`) to also create email alerts: 3+ failed logins/hour, COPY errors, and monthly credits above 60. Alerts run on `MONITOR_WH` hourly, so they cost a little: keep the schedule at 60 minutes.

`ACCOUNT_USAGE` data lags by up to a few hours; use `INFORMATION_SCHEMA` table functions for real time. Cloud mapping: these views ≈ CloudTrail + CloudWatch metrics / Cloud Audit Logs + Monitoring.

## 2. Identity and network hardening
`governance` creates (but does **not** enforce) `NP_HANDSON`, `AP_HUMAN` (MFA required), `SP_HUMAN` (30 min idle) and creates `AP_SERVICE` (key-pair only); `scripts/apply-policies` attaches `AP_SERVICE` to the `TERRAFORM` user.

**If you will set up CI ([guide 08](08-ci-and-apply.md)), skip account enforcement:** leave `enforce_account_policies` at `false`, in `terraform.tfvars` and in `TFVARS_JSON`. The flag attaches `NP_HANDSON` and `AP_HUMAN` to the whole account. An account [network policy](https://docs.snowflake.com/en/user-guide/network-policies) applies to every user who has no more specific one, including `TERRAFORM` and the plan user, so GitHub-hosted runners could not sign in. Both policies then stay unattached. If you already enforced them, set the flag to `false` and apply before guide 08.

Only if you will **not** use CI, enforce on the account:
1. Confirm your MFA is enrolled, then set `allowed_ips = ["<your public IP>/32"]` and `enforce_account_policies = true` in the git-ignored `terraform/envs/handson/terraform.tfvars`. Do not pass the flag with `-var`: a later apply without it would detach the policies.
2. Apply:
```bash
source scripts/tf-env
terraform -chdir=terraform/envs/handson apply
```
Keep a second admin session open while testing: a wrong IP locks you out.

## 3. Audit and Trust Center
`sql/audit.sql` answers: who read HEALTH columns this week, which grants changed, and where RAW data flows. In Snowsight open **Governance & security > Trust Center**, enable the CIS benchmark scanner, read the findings (MFA/network-policy findings remain unless section 2 is enforced, which CI users skip), and fix one.

## Cost of this step (monitoring)
About 4 credits (hourly alerts plus queries on `MONITOR_WH`).

## Verify (monitoring)

```bash
snow sql -c handson_tf --warehouse MONITOR_WH -q "SELECT * FROM HANBIT_OPS.MONITORING.V_CREDITS_BY_SERVICE ORDER BY DAY DESC LIMIT 5"
snow sql -c handson_tf --warehouse MONITOR_WH -f sql/audit.sql
scripts/verify-step 07 --execute
```
Expect rows from the credits view (ACCOUNT_USAGE lags by up to a few hours, so a brand-new account may show none yet; the verify step passes with zero rows) and the audit query listing the access-matrix reads.

## 4. FinOps: know the number before it knows you
```bash
scripts/cost-report            # credits by service vs plan 53 / warn 70 / hard stop 80 (exit 2 at 70+)
scripts/cost-guard --status    # resource monitors and warehouses
scripts/cost-guard --suspend-all --execute
```
Layers of protection, cheapest first: warehouse `auto_suspend = 60`; per-warehouse resource monitors (created by `scripts/bootstrap`, attached by `scripts/attach-monitors`); the account monitor `HANDSON_ACCOUNT_MONITOR` with a hard stop at 80 credits (created by `scripts/bootstrap`); and this report. `ACCOUNT_USAGE` lags up to about 3 hours, so for warehouses the monitor, not the report, is the real brake. Credits are an estimate until you confirm the Seoul rate in `scripts/preflight`.

**What the monitors do not cover:** [resource monitors](https://docs.snowflake.com/en/user-guide/resource-monitors) work for warehouses only. They neither count nor stop serverless features, such as the data quality checks from guide 05 (`DATA_QUALITY_MONITORING` in the report), serverless tasks or Snowpipe Streaming. Watch those lines in `scripts/cost-report`, or add a [budget](https://docs.snowflake.com/en/user-guide/budgets). `scripts/cost-guard --suspend-all --execute` suspends warehouses, Dynamic Tables and their data quality checks, but not alerts, tasks or pipes. To resume, see guide 05.

## 5. Teardown
`terraform destroy` reads its credentials from `SNOWFLAKE_*` variables, and `scripts/teardown` does not load them. Run all of this in one shell, from the repo root:
```bash
read -rs PRIVATE_KEY_PASSPHRASE && export PRIVATE_KEY_PASSPHRASE   # type the passphrase, then Enter
source scripts/tf-env                                              # exports the variables Terraform reads
scripts/teardown               # preview
scripts/teardown --execute --yes  # suspend compute, terraform destroy, drop OPS db, monitors, TERRAFORM user, TF_ADMIN
```
The `snow sql -c handson_admin` steps inside the script keep the user, role and key of that connection. It is destructive: without `--execute` it only previews, and with `--execute` it refuses to run without `--yes`. Afterwards delete the local `~/.snowflake/*.p8` keys you generated.

## Cost of this step (FinOps and teardown)
Under 0.5 credits; teardown stops all recurring cost.

## Verify (FinOps and teardown)

```bash
scripts/cost-report                                       # total credits and status vs plan 53 / warn 70 / stop 80
scripts/cost-guard --status
# after scripts/teardown --execute --yes (while the admin key still exists):
snow sql -c handson_admin -q "SHOW WAREHOUSES"            # none of LOAD_WH, TRANSFORM_WH, BI_WH, MONITOR_WH
snow sql -c handson_admin -q "SHOW RESOURCE MONITORS"     # no *_WH_MONITOR and no HANDSON_ACCOUNT_MONITOR
snow sql -c handson_admin -q "SHOW USERS LIKE 'TERRAFORM'"   # no rows
```
After teardown the `handson_tf` connection no longer works, so use `handson_admin` for these checks.

---
<!-- nav:bottom -->
[🏠 7-day map](../../README.md#7-day-map) · ← [06 BI & AI](06-bi-and-ai.md) · [08 CI & apply](08-ci-and-apply.md) →
<!-- /nav:bottom -->
