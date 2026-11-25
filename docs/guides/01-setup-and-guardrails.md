# 01 · Setup and guardrails

<!-- nav:top -->
[🏠 7-day map](../../README.md#7-day-map) · ← [00 Orientation](00-orientation.md) · [02 RBAC & Terraform](02-rbac-and-terraform.md) →
<!-- /nav:top -->

**Japanese version:** [../ja/guides/01-setup-and-guardrails.md](../ja/guides/01-setup-and-guardrails.md)

Order matters: tools → connection → preflight → guardrails (resource monitor) → anything that uses compute.

## 1. Install tools
```bash
scripts/install-tools --dry-run   # see the plan
scripts/install-tools             # terraform, snow (SnowCLI), shellcheck, gitleaks; safe to re-run
```

## 2. Create the admin connection (human, MFA)
1. Sign in to Snowsight with your trial user and enable MFA (Profile > Authentication).
2. Copy `config/connections.toml.example` to `~/.snowflake/connections.toml`, fill in `<org>-<account>` and your user, `chmod 600`.
3. `snow connection test -c handson_admin` should print `Status OK`.

The real file lives outside the repo and is git-ignored. **Cloud mapping:** this is like an `aws sso login` profile; the Terraform service identity (guide 02) is like a workload IAM role.

## 3. Run preflight
```bash
scripts/preflight --dry-run
scripts/preflight
```
It checks tools, connection, region, edition, the Cortex cross-region parameter (read-only, never changed), whether Snowflake-managed Iceberg storage works (creates and drops a scratch table), and asks for your real credit rate from Snowsight (Admin > Cost Management).

| Result | Meaning | Fallback |
|---|---|---|
| `block` edition | Policies need Enterprise | Use an Enterprise trial |
| `warn` iceberg | Snowflake storage unavailable | Iceberg becomes conceptual + appendix |
| `warn` cortex | CoCo/Cortex may be unavailable | Skip AI labs, stay in-region (no cross-region inference) |

**What I observed (fill in, redact account id):** region ___, edition ___, rate ___, Iceberg probe ___, Cortex ___.

## Cost of this step
About 0.1 credit (a few seconds of an XS warehouse for the probe).

## Verify
`scripts/preflight` exits 0 and prints no `block` rows.

## 4. Guardrails before workloads
```bash
scripts/bootstrap --dry-run      # prints every SQL statement; nothing is executed
scripts/bootstrap --quota 80     # account resource monitor, TF_ADMIN role, TERRAFORM service user + key pair
scripts/cost-guard --status
```
- **Account resource monitor** `HANDSON_ACCOUNT_MONITOR`: quota 80 credits, notify at 50/75/90 %, suspend at 95 %, `SUSPEND_IMMEDIATE` at 100 %. It must be set by `ACCOUNTADMIN`, so the script creates it, not Terraform.
- **Why 80 and not 88:** at $4.50/credit $400 is about 88 credits; the gap is a safety margin for credits that bill after a monitor trips. Recompute with your real rate: `--quota $(( 400 * 100 / (rate_cents) ))`, then subtract 10 %.
- **Service identity:** user `TERRAFORM` (`TYPE = SERVICE`, key-pair only, no password) with role `TF_ADMIN`, which gets only the account privileges Terraform needs. The key is encrypted with a passphrase you type; it lives in `~/.snowflake/`, never in the repo. Export `PRIVATE_KEY_PASSPHRASE` in your shell when running Terraform.
- **Warehouse monitors** (Terraform `finops` module): one per warehouse, notify 75/90, suspend 100.
- **Emergency stop:** `scripts/cost-guard --suspend-all`.

Cloud mapping: resource monitor ≈ AWS Budgets action / GCP budget with a Pub/Sub kill switch, but enforced by the platform itself.

## Cost of this step (continued)
0 credits: the monitor and roles are metadata only.

## Verify (guardrails)
`scripts/cost-guard --status` lists `HANDSON_ACCOUNT_MONITOR` with quota 80.

---
<!-- nav:bottom -->
[🏠 7-day map](../../README.md#7-day-map) · ← [00 Orientation](00-orientation.md) · [02 RBAC & Terraform](02-rbac-and-terraform.md) →
<!-- /nav:bottom -->
