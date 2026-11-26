# 00 · Orientation

<!-- nav:top -->
[🏠 7-day map](../../README.md#7-day-map) · [01 Setup](01-setup-and-guardrails.md) →
<!-- /nav:top -->

**Audience:** data engineers who know AWS/GCP (or similar) and are new to Snowflake.
**Scenario:** Hanbit Insurance & Capital (fictional): underwriting, claims (health data), lending (credit data), finance, risk/fraud, marketing.
**Japanese version:** [../ja/guides/00-orientation.md](../ja/guides/00-orientation.md)

## How Snowflake maps to what you know
| Snowflake | Closest cloud concept | Key difference |
|---|---|---|
| Account / region | Cloud project/account | One account holds all databases and compute |
| Virtual warehouse | Ephemeral query cluster (EMR, Dataproc) | Billed per second while running; suspend aggressively |
| Database / schema | Dataset / catalog | Grants are on these objects |
| Role (RBAC) | IAM role | Users hold roles; privileges go to roles only |
| Tag + masking policy | Lake Formation / BigQuery policy tags | Policies attach to tags, so they scale |
| Row access policy | Row-level security | Driven by a mapping table: access is data, not code |
| Storage integration | IAM role trust | Not needed in the core path (see appendix) |

## Security baseline (this repo models what it teaches)
- No account ids, passwords, tokens, keys or Terraform state are committed. Templates are `*.example`.
- Service users use key-pair authentication; humans use MFA in the browser. `ACCOUNTADMIN` is for bootstrap only, through a
  short-lived key-pair admin connection that you remove at teardown (guide 01).
- Data is synthetic and seeded; ID numbers have an invalid check digit so they match no real person.
- Run `scripts/check-secrets` before every commit.

## Cost plan (credits; $4.50/credit assumed, you verify the real rate on day 1)
| Area | Credits |
|---|---|
| Setup, Terraform, policy tests | 4 |
| Ingestion | 8 |
| Transform | 8 |
| BI | 8 |
| Governance | 6 |
| Monitoring | 4 |
| CoCo / Cortex (daily cap) | 15 |
| **Planned** | **~53** |
| Reserve / hard stop | ~20 / 80 |

Guardrails (resource monitor, auto-suspend 60 s) are created **before** any workload.

## Scripts preview by default
A script that changes something (Snowflake, GitHub, your machine or the repo files) only shows what it would do, and ends with `[preview] nothing was changed`. Add `--execute` to act (`scripts/teardown` also needs `--yes`). Read-only checks such as `scripts/check-secrets`, `scripts/cost-report`, `scripts/cost-guard --status` and `scripts/access-matrix` need no flag.

## Start every session
Every new terminal needs the key passphrase; Terraform commands also need `scripts/tf-env`. Scripts use the `handson_tf` connection (role `TF_ADMIN`) unless a guide says `handson_admin` (`ACCOUNTADMIN`: bootstrap, `attach-monitors`, teardown).
```bash
cd snowflake-handson
read -rs "PRIVATE_KEY_PASSPHRASE?Key passphrase: " && echo && export PRIVATE_KEY_PASSPHRASE   # zsh; bash: read -rsp 'Key passphrase: ' PRIVATE_KEY_PASSPHRASE; echo; export PRIVATE_KEY_PASSPHRASE
source scripts/tf-env      # only before terraform commands (guides 02, 04, 05, 07)
```
Each guide ends with a **Verify** block: the exact commands, what to expect, and where to see the same state in Snowsight. `scripts/verify-step N` runs the read-only check; add `--execute` to also record it in `.progress/state.json`.

## Cost of this step
0 credits (reading only).

## Verify

```bash
scripts/verify-step 00 --execute  # runs scripts/check-secrets; no Snowflake connection
cat .progress/state.json      # one UTC timestamp per verified step
```
Expect `[check-secrets] clean`, then `[info] step 00 verified; recorded in .progress/state.json`.

---
<!-- nav:bottom -->
[🏠 7-day map](../../README.md#7-day-map) · [01 Setup](01-setup-and-guardrails.md) →
<!-- /nav:bottom -->
