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
`governance` creates (but does **not** enforce) `NP_HANDSON`, `AP_HUMAN` (MFA required), `SP_HUMAN` (30 min idle) and attaches `AP_SERVICE` (key-pair only) to the `TERRAFORM` user. To enforce on the account:
1. Set `allowed_ips = ["<your public IP>/32"]` and confirm your MFA is enrolled.
2. `terraform apply -var enforce_account_policies=true`.
Keep a second admin session open while testing: a wrong IP locks you out.

## 3. Audit and Trust Center
`sql/audit.sql` answers: who read HEALTH columns this week, which grants changed, and where RAW data flows. In Snowsight open **Governance & security > Trust Center**, enable the CIS benchmark scanner, read the findings (expect MFA/network-policy findings until section 2 is enforced), and fix one.

## Cost of this step (monitoring)
About 4 credits (hourly alerts plus queries on `MONITOR_WH`).

## Verify (monitoring)
`SELECT * FROM HANBIT_OPS.MONITORING.V_CREDITS_BY_SERVICE ORDER BY DAY DESC LIMIT 5;` returns rows; the audit query lists the access-matrix reads.

## 4. FinOps: know the number before it knows you
```bash
scripts/cost-report            # credits by service vs plan 53 / warn 70 / hard stop 80 (exit 2 at 70+)
scripts/cost-guard --status    # warehouses, monitors, dynamic tables
scripts/cost-guard --suspend-all
```
Layers of protection, cheapest first: warehouse `auto_suspend = 60`; per-warehouse resource monitors (Terraform `finops`); the account monitor `HANDSON_ACCOUNT_MONITOR` with a hard stop at 80 credits (created by `scripts/bootstrap`); and this report. `ACCOUNT_USAGE` lags up to about 3 hours, so the monitor, not the report, is the real brake. Credits are an estimate until you confirm the Seoul rate in `scripts/preflight`.

## 5. Teardown
```bash
scripts/teardown --dry-run     # preview
scripts/teardown --yes         # suspend compute, terraform destroy, drop OPS db, monitor, TERRAFORM user, TF_ADMIN
```
It is destructive and refuses to run without `--yes`. Afterwards delete the local `~/.snowflake/*.p8` keys you generated.

## Cost of this step (FinOps and teardown)
Under 0.5 credits; teardown stops all recurring cost.

## Verify (FinOps and teardown)
`scripts/cost-report` prints a total and status; after teardown `SHOW WAREHOUSES` lists none of ours.

---
<!-- nav:bottom -->
[🏠 7-day map](../../README.md#7-day-map) · ← [06 BI & AI](06-bi-and-ai.md) · [08 CI & apply](08-ci-and-apply.md) →
<!-- /nav:bottom -->
