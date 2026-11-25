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

## 2. Create the admin connection (key pair)
Trial accounts, including ones created with Google sign-in, have no SSO identity provider. `authenticator = "EXTERNALBROWSER"`
fails there with error 390190, and the CLI cannot reuse a Google or Snowsight browser login. Use a key pair instead.
1. Sign in to Snowsight with your trial user and enable MFA for the browser login (Profile > Authentication, if offered).
2. Generate an encrypted key. It stays in `~/.snowflake/`, never in the repo; choose a passphrase when asked:
   ```bash
   mkdir -p ~/.snowflake && chmod 700 ~/.snowflake
   openssl genrsa 2048 | openssl pkcs8 -topk8 -v2 aes256 -inform PEM -out ~/.snowflake/handson_admin_key.p8
   openssl rsa -in ~/.snowflake/handson_admin_key.p8 -pubout -out ~/.snowflake/handson_admin_key.pub
   chmod 600 ~/.snowflake/handson_admin_key.p8
   grep -v -- '-----' ~/.snowflake/handson_admin_key.pub | tr -d '\n'   # the public key as one line, for the next step
   ```
3. In a Snowsight SQL worksheet (**Projects > Worksheets > + > SQL Worksheet**, role `ACCOUNTADMIN`) run `SELECT CURRENT_USER();`,
   then register the key. Quote the name exactly as printed; users created by Google sign-in are lower case, and an unquoted
   name is upper-cased and fails with `User '...' does not exist or not authorized`:
   ```sql
   ALTER USER "<name from CURRENT_USER()>" SET RSA_PUBLIC_KEY='<one-line public key>';
   DESC USER "<name from CURRENT_USER()>";   -- note LOGIN_NAME; RSA_PUBLIC_KEY_FP must now be set
   ```
   Snowflake also offers a named form, `ALTER USER ... ADD KEY PAIR`, which supports expiry; see the
   [key-pair documentation](https://docs.snowflake.com/en/user-guide/key-pair-auth).
4. Copy `config/connections.toml.example` to `~/.snowflake/connections.toml`, set `<org>-<account>`, set `user` to the
   `LOGIN_NAME` from step 3 (often your email, and not always what `CURRENT_USER()` shows), `chmod 600`.
5. Give the CLI the passphrase for this shell (not stored anywhere), then test:
   ```bash
   read -rs "PRIVATE_KEY_PASSPHRASE?Key passphrase: " && echo && export PRIVATE_KEY_PASSPHRASE   # zsh; in bash: read -rsp 'Key passphrase: ' PRIVATE_KEY_PASSPHRASE
   snow connection test -c handson_admin
   ```
   It should print `Status | OK` with role `ACCOUNTADMIN`. Export the passphrase again in every new terminal.

| Error | Cause and fix |
|---|---|
| `390190 ... SAML Identity Provider account parameter` | The profile uses `EXTERNALBROWSER` and the account has no SSO; switch to `SNOWFLAKE_JWT` as above |
| `Encrypted private key, you must provide the passphrase` | Export `PRIVATE_KEY_PASSPHRASE` in this shell |
| `User '...' does not exist or not authorized` | Quote the name in the exact case `CURRENT_USER()` printed, and use role `ACCOUNTADMIN` |
| JWT or "user not found" from the CLI | Set `user` to the `LOGIN_NAME` from `DESC USER` |

The real file lives outside the repo and is git-ignored. This admin key is a long-lived `ACCOUNTADMIN` credential: after
bootstrap and teardown, run `ALTER USER "<name>" UNSET RSA_PUBLIC_KEY;` and delete `~/.snowflake/handson_admin_key.*`.
**Cloud mapping:** like an AWS CLI profile with a passphrase-protected static key; the Terraform service identity (guide 02) is like a workload IAM role.

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

```bash
scripts/preflight                       # exit 0 and no `block` rows
snow connection test -c handson_admin   # Status: OK
scripts/verify-step 01
```
Expect `[info] step 01 verified`. If the connection test fails, see the error table in step 2.

## 4. Guardrails before workloads
```bash
scripts/bootstrap --dry-run      # prints every SQL statement; nothing is executed
scripts/bootstrap --quota 80     # account + per-warehouse resource monitors, TF_ADMIN role, TERRAFORM service user + key pair
scripts/cost-guard --status
```
- **Account resource monitor** `HANDSON_ACCOUNT_MONITOR`: quota 80 credits, notify at 50/75/90 %, suspend at 95 %, `SUSPEND_IMMEDIATE` at 100 %. It must be set by `ACCOUNTADMIN`, so the script creates it, not Terraform.
- **Why 80 and not 88:** at $4.50/credit $400 is about 88 credits; the gap is a safety margin for credits that bill after a monitor trips. Recompute with your real rate: `--quota $(( 400 * 100 / (rate_cents) ))`, then subtract 10 %.
- **Service identity:** user `TERRAFORM` (`TYPE = SERVICE`, key-pair only, no password) with role `TF_ADMIN`, which gets only the account privileges Terraform needs. The key is encrypted with the passphrase in `PRIVATE_KEY_PASSPHRASE` (the one you exported for the admin key, so a single export serves both connections; bootstrap refuses to run without it). It lives in `~/.snowflake/`, never in the repo. Keep `PRIVATE_KEY_PASSPHRASE` exported when running Terraform.
- **Warehouse monitors:** `scripts/bootstrap` also creates one per warehouse (`LOAD_WH_MONITOR` 10, `TRANSFORM_WH_MONITOR` 10, `BI_WH_MONITOR` 10, `MONITOR_WH_MONITOR` 5 credits; notify 75/90, suspend 100, suspend immediately 110). Only `ACCOUNTADMIN` can create a resource monitor or attach one to a warehouse, so Terraform (`TF_ADMIN`) does neither. After guide 02's `terraform apply`, run `scripts/attach-monitors`.
- **Emergency stop:** `scripts/cost-guard --suspend-all`.

Cloud mapping: resource monitor ≈ AWS Budgets action / GCP budget with a Pub/Sub kill switch, but enforced by the platform itself.

## Cost of this step (continued)
0 credits: the monitor and roles are metadata only.

## Verify (guardrails)

```bash
scripts/cost-guard --status                              # JSON: resource_monitors, then warehouses (none yet)
snow sql -c handson_admin -q "SHOW USERS LIKE 'TERRAFORM'"
snow connection test -c handson_tf                       # the new service identity: Status: OK
```
Expect:
- `HANDSON_ACCOUNT_MONITOR` with `level` `ACCOUNT`, `credit_quota` `80.00`; and four warehouse monitors (`LOAD_WH_MONITOR` 10, `TRANSFORM_WH_MONITOR` 10, `BI_WH_MONITOR` 10, `MONITOR_WH_MONITOR` 5).
- One `TERRAFORM` user row (type `SERVICE`).
- The same monitors in Snowsight: **Admin > Cost management > Resource monitors** (role `ACCOUNTADMIN`).

---
<!-- nav:bottom -->
[🏠 7-day map](../../README.md#7-day-map) · ← [00 Orientation](00-orientation.md) · [02 RBAC & Terraform](02-rbac-and-terraform.md) →
<!-- /nav:bottom -->
