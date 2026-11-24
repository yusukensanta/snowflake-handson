# 00 · Orientation

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
- Service users use key-pair authentication; humans use MFA; `ACCOUNTADMIN` is for bootstrap only.
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

## Cost of this step
0 credits (reading only).

## Verify
`scripts/check-secrets` prints `[check-secrets] clean`.
