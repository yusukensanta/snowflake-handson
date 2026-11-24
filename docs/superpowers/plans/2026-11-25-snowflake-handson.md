# Snowflake Hands-On (Insurance & Financing) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a public, reproducible tutorial repo (guides, Terraform, scripts, Claude Code skills/commands) that takes a cloud-experienced engineer through a governed Snowflake pipeline for a fictional insurance and lending group, within a $400 trial budget.

**Architecture:** Guides drive a 7-day path. Terraform provisions Snowflake objects; SQL covers provider gaps; Python (`uv`) provides the data generator, Snowpipe Streaming loader, cost report and access-matrix runner; bash wraps them as idempotent, `--dry-run`-capable scripts; `.claude/` commands and skills wrap the scripts. Governance is proven by an access matrix, not asserted.

**Tech Stack:** Snowflake (Enterprise, AWS `ap-northeast-2`), Terraform + `snowflakedb/snowflake` provider (pin latest at Task 2), SnowCLI (`snow`), Python 3 + `uv` + `ruff` + `pytest`, `snowflake-connector-python`, Snowpipe Streaming high-performance Python SDK, Streamlit in Snowflake, `mise`, `shellcheck`, `gitleaks`.

**Spec:** `docs/superpowers/specs/2026-11-25-snowflake-handson-design.md`

## Global Constraints

- Budget $400, planned at **$4.50/credit ≈ 88 credits**; planned use ~53, reserve ~20, **account resource monitor hard stop 80 credits** (`SUSPEND_IMMEDIATE`). Created before any compute-using step.
- `AUTO_SUSPEND = 60` seconds and `STATEMENT_TIMEOUT_IN_SECONDS` set on every warehouse; XS only.
- Region `AWS ap-northeast-2`, Enterprise edition. No AWS account of the owner: core path uses internal stage, Snowpipe Streaming, Snowflake-managed Iceberg storage. S3/IAM material is an optional appendix, never applied by the owner.
- No `ACCOUNTADMIN` for routine work; a least-privilege `TERRAFORM` service user with key-pair auth; humans use MFA; no passwords in scripts.
- **Public repo:** never commit account identifiers, user names, passwords, tokens, private keys, PATs, `*.tfstate`, filled `*.tfvars`, `connections.toml`. Templates are `*.example`. Data is synthetic, fixed seed, obviously fake IDs (invalid check digit).
- Owner's rules: **never run `git commit`/`git push` unless the owner asks**; no CI exists, so propose a GitHub Actions workflow (test, lint, secret scan) at the end and ask first. Python ships with tests at ≥80% coverage; shell/Terraform are verified by running (`shellcheck`, `bash -n`, `terraform fmt -check`/`validate`, `--dry-run`).
- Every guide ends with a "Cost of this step" box (credits) and a "Verify" section with a command and expected output; all docs in English.
- Cut order if cost or time slips: CoCo/Cortex depth → Streamlit extras and monitoring v2 → open-engine read → Iceberg lab. Never cut: RBAC, Terraform, ingestion, masking/row policies, access matrix, cost guardrails, teardown.
- If CoCo/Cortex is unavailable in Seoul: skip AI labs, stay in-region, no cross-region inference.
- Unverified facts (Seoul credit rate, Seoul Iceberg storage, CoCo in Seoul, Terraform resource names) must be checked by Task 2's preflight or against pinned docs, with doc URL and date recorded in the guide.

## Review Focus

1. Re-running any script/Terraform twice (idempotency): second run changes nothing and exits 0.
2. Real credit rate differs from $4.50: cost report and guardrail sizes derive from the account's rate, not the constant.
3. A feature unavailable in Seoul (Iceberg storage, CoCo): preflight prints the named fallback and exits non-zero only for blocking items.
4. A secret-like string (private key header, token) in any tracked file: `check-secrets` fails.
5. Access matrix where a role is *denied* versus *query errors for other reasons*: only genuine policy outcomes pass; infrastructure errors fail loudly.
6. `teardown` run when objects are already gone or partially created: completes and reports what remains billable.
7. Generator run with the same seed on another machine: byte-identical output.

---

## File Structure

```
CLAUDE.md  README.md  .gitignore  .gitleaks.toml  .pre-commit-config.yaml  pyproject.toml
docs/guides/00-orientation.md 01-setup-and-guardrails.md 02-rbac-and-terraform.md
            03-ingestion.md 04-governance.md 05-transform-and-iceberg.md
            06-bi-and-ai.md 07-monitoring-finops-teardown.md appendix-aws.md
terraform/modules/{bootstrap,finops,databases,governance,ingestion,monitoring,appendix_aws_landing}
terraform/envs/handson/{main.tf,variables.tf,versions.tf,terraform.tfvars.example}
sql/{iceberg.sql,streamlit.sql,semantic_view.sql,dmf.sql}  sql/matrix/access-matrix.yaml
src/hanbit_gen/{schema.py,fakers.py,cli.py}   src/sfops/{conn.py,cost.py,matrix.py,streaming.py}
tests/{test_gen_*.py,test_conn.py,test_cost.py,test_matrix.py,test_streaming.py}
scripts/{lib/common.sh,install-tools,preflight,bootstrap,gen-data,load-batch,stream-load,
         access-matrix,cost-report,cost-guard,teardown,check-secrets}
apps/streamlit/{app.py,environment.yml}
.claude/commands/{sf-preflight,sf-next,sf-cost,sf-verify,sf-access-test,sf-teardown}.md
.claude/skills/{snowflake-handson-guide,snowflake-governance-review,snowflake-cost-watch,snowflake-terraform-workflow}/SKILL.md
.progress/ (gitignored)  *.example templates
```

---

### Task 1: Repo scaffold and public-repo security baseline

**Files:** Create `.gitignore`, `.gitleaks.toml`, `.pre-commit-config.yaml`, `scripts/check-secrets`, `scripts/lib/common.sh`, `pyproject.toml` (uv project, `ruff`, `pytest`, `pytest-cov`), `CLAUDE.md`, `README.md`, `docs/guides/00-orientation.md`.
**Interfaces:** Produces `scripts/lib/common.sh` with `log_info`, `log_err`, `require_cmd <name>`, `run <cmd...>` (honours `DRY_RUN=1`, printing instead of executing), and `parse_common_flags "$@"` (sets `DRY_RUN` from `--dry-run`). Every later script sources it. Produces `scripts/check-secrets` (exit 0 clean, 1 on finding).

- [ ] **Step 1:** Write `tests/test_secrets_scan.sh`-style check as a script `scripts/check-secrets --self-test`: creates temp files holding a PEM private-key header, an account hostname and a password assignment, asserts the scan exits 1; then a clean temp file, asserts exit 0.
- [ ] **Step 2:** Run it; expect failure (script missing).
- [ ] **Step 3:** Implement `scripts/check-secrets` wrapping `gitleaks detect --no-git` with `.gitleaks.toml` (default rules plus a custom rule for Snowflake account-identifier-looking hosts `*.snowflakecomputing.com` and `*.p8`/`*.pem` paths). `.gitignore` covers `*.tfstate*`, `.terraform/`, `*.tfvars` (not `*.tfvars.example`), `*.p8`, `*.pem`, `connections.toml`, `.env*`, `.progress/`, `__pycache__`, `.venv`, `data/out/`.
- [ ] **Step 4:** Implement `common.sh`; write `CLAUDE.md` (<100 lines: purpose, commands, layout, the Global Constraints that matter day to day); `README.md` with the 7-day map and a cost box; guide 00 (audience, how the repo is organised, security baseline and why, cost table from spec §4).
- [ ] **Step 5:** Verify: `scripts/check-secrets --self-test` passes; `shellcheck scripts/**`; `uv run ruff check`; `uv run pytest` (empty suite passes). Do not commit.

### Task 2: Tool install and preflight

**Files:** Create `scripts/install-tools`, `scripts/preflight`, `tests/test_preflight_parse.py`, `docs/guides/01-setup-and-guardrails.md` (first half).
**Interfaces:** Consumes `common.sh`. Produces `scripts/preflight [--dry-run] [--connection NAME]` printing a table of checks `{name, status: ok|warn|block, detail, fallback}` and exit code 1 only if any `block`. Parsing helpers live in `src/sfops/preflight.py`: `parse_rate(raw: str) -> float`, `parse_edition(raw: str) -> str`, `PreflightError`.

- [ ] **Step 1:** Write `scripts/install-tools` to install `terraform`, `snow` (SnowCLI via `uv tool`), `shellcheck`, `gitleaks` through `mise`, idempotent, `--dry-run` prints plan. Verify twice-run output on a clean-ish machine: second run reports "already installed".
- [ ] **Step 2:** Check latest Terraform provider `snowflakedb/snowflake` release and pin it in a note in the guide; record the exact version used in `terraform/envs/handson/versions.tf` (Task 5).
- [ ] **Step 3:** Implement `preflight` checks: tool versions; `snow connection test`; account edition, region and credit rate read via SQL (`SHOW PARAMETERS`/organisation or Usage views where available, otherwise prompt the owner to type the rate shown in Snowsight); CoCo availability and `CORTEX_ENABLED_CROSS_REGION` value (read-only, never changed); Iceberg Snowflake-storage capability probe (create and drop a throwaway Iceberg table in a scratch schema, XS, measured credits noted). Each failing feature maps to its named fallback (spec §3).
- [ ] **Step 4:** Test `tests/test_preflight_parse.py`: given canned `snow sql --format json` output, `parse_rate(...) == 4.30`-style float and edition `ENTERPRISE`; unknown output raises `PreflightError`.
- [ ] **Step 5:** Verify: `preflight --dry-run` lists every check with no side effects; owner runs it live and pastes results (redact account id) into the guide's "What I observed" box.

### Task 3: Bootstrap identity and guardrails (guardrails before compute)

**Files:** Create `scripts/bootstrap`, `terraform/modules/bootstrap`, `terraform/modules/finops`, `terraform/envs/handson/{main.tf,variables.tf,versions.tf,terraform.tfvars.example}`, `scripts/cost-guard`, `docs/guides/01-setup-and-guardrails.md` (second half), `docs/guides/02-rbac-and-terraform.md` (RBAC part).
**Interfaces:** `scripts/bootstrap` (run once, as the owner via `ACCOUNTADMIN`/browser MFA): generates an encrypted key pair under `~/.snowflake/` (passphrase prompted, never echoed or stored), creates role `TF_ADMIN` and service user `TERRAFORM` with `RSA_PUBLIC_KEY`, grants minimal privileges to create roles, databases, warehouses, monitors; writes `~/.snowflake/connections.toml` entries `handson_tf`; prints nothing secret. `terraform/modules/finops` outputs `account_monitor_name`; `modules/bootstrap` outputs `warehouse_names` map (`LOAD_WH`, `TRANSFORM_WH`, `BI_WH`, `MONITOR_WH`, all XS). `scripts/cost-guard [--suspend-all|--status]`.

- [ ] **Step 1:** Implement `scripts/bootstrap` with idempotent `CREATE ... IF NOT EXISTS`/key-rotation guard; `--dry-run` prints SQL only. Verify with `--dry-run`, then live.
- [ ] **Step 2:** `modules/finops`: account resource monitor, credit quota 80, triggers notify 50/75/90, suspend at 100 and `SUSPEND_IMMEDIATE` at 100 of hard stop; per-warehouse monitors (quota from budget table spec §4); budget object where the provider supports it, else `sql/` fallback. Variable `credit_rate_usd` default 4.50, `hard_stop_credits` default 80.
- [ ] **Step 3:** `modules/bootstrap`: account roles hierarchy skeleton (`DATA_PLATFORM_ENGINEER`, `SECURITY_ADMIN_FN`, `AUDITOR`, others per spec §6 as empty functional roles), four warehouses with auto-suspend 60 and statement timeout, `MONITOR_WH` smallest.
- [ ] **Step 4:** Verify: `terraform fmt -check -recursive`, `terraform validate`, `terraform plan` shows the resource monitor and warehouses; owner applies; second `plan` shows "No changes" (Review Focus 1). `cost-guard --status` prints monitor state; `--suspend-all` suspends warehouses (test on live, then resume).
- [ ] **Step 5:** Guide: why a service user and key-pair (maps to IAM roles/workload identity), why monitors precede workloads.

### Task 4: Import lab

**Files:** Create `terraform/envs/handson/import-lab/` (README-guided `import.tf.example`), section in `docs/guides/02-rbac-and-terraform.md`.
**Interfaces:** None consumed by later tasks.

- [ ] **Step 1:** Guide steps: create role `LAB_IMPORT_ROLE` and warehouse `LAB_IMPORT_WH` by hand in Snowsight; write matching config; add `import {}` blocks; `terraform plan` shows imports only; apply; second plan "No changes"; then alter the warehouse size in Snowsight and show drift in `plan`.
- [ ] **Step 2:** Verify by running the lab once; expected final output "No changes. Your infrastructure matches the configuration."; remove the lab objects via `terraform destroy -target=...`.

### Task 5: Synthetic data generator (TDD)

**Files:** Create `src/hanbit_gen/{schema.py,fakers.py,cli.py}`, `tests/test_gen_schema.py`, `tests/test_gen_determinism.py`, `tests/test_gen_fake_ids.py`, `scripts/gen-data`.
**Interfaces:** `scripts/gen-data --emit-tag-map PATH` writes `{table.column: sensitivity}` JSON for Task 7. Produces `hanbit_gen.generate(domain: str, seed: int, rows: int, out_dir: Path) -> Path` writing `<domain>.csv.gz` (NDJSON variant via `fmt: Literal["csv","ndjson"]="csv"`). Domains: `underwriting, claims, lending, finance, risk_fraud, marketing`. `fake_rrn(rng) -> str` returns a 13-digit Korean-RRN-shaped string with an **intentionally invalid check digit**. Columns are fixed by `schema.SCHEMAS: dict[str, list[Column]]` with `Column(name, type, sensitivity: Literal["none","pii","health","credit","financial"])`; sensitivity labels are reused by Task 7 tagging.

- [ ] **Step 1:** Tests (names + assertions): `test_same_seed_same_bytes` (two runs hash equal, Review Focus 7); `test_fake_rrn_check_digit_always_invalid` (1000 samples, validator rejects all); `test_every_domain_has_schema_and_file`; `test_claims_contains_health_columns` (`diagnosis_code` marked `health`); `test_region_values_limited_to_known_set` (shared `REGIONS` constant for Task 7's row policy); `test_rows_param_respected`; `test_cli_rejects_unknown_domain`.
- [ ] **Step 2:** Run `uv run pytest`; expect failures.
- [ ] **Step 3:** Implement with `random.Random(seed)` only (no wall-clock, no `faker` global state); target about 200 MB total at default scale; `scripts/gen-data [--rows N] [--out data/out]`.
- [ ] **Step 4:** Verify: `uv run pytest --cov=hanbit_gen --cov-fail-under=80` passes; `uv run ruff check`; total output size under 250 MB.

### Task 6: Ingestion (batch and streaming)

**Files:** Create `terraform/modules/ingestion`, `terraform/modules/databases` (RAW part), `src/sfops/{conn.py,streaming.py}`, `scripts/{load-batch,stream-load}`, `tests/{test_conn.py,test_streaming.py}`, `docs/guides/03-ingestion.md`.
**Interfaces:** `sfops.conn.connect(connection_name: str, role: str | None = None) -> SnowflakeConnection` (reads `~/.snowflake/connections.toml`; raises `ConnectionConfigError` with a message pointing to `bootstrap` when the entry is missing; never logs credentials). `sfops.streaming.stream_file(conn_name: str, domain: str, path: Path, batch_size: int = 5000) -> int` returns rows sent and uses the high-performance Python SDK with key-pair auth. Produces databases `HANBIT_RAW` with one schema per domain and tables created from `hanbit_gen.schema.SCHEMAS`; internal stage `RAW.<domain>_STAGE`.

- [ ] **Step 1:** Tests: `test_connect_missing_entry_raises_config_error`; `test_connect_never_logs_secret` (capture logs, assert no key material); `test_stream_file_batches_rows` (fake SDK client records batch sizes, 12 rows with `batch_size=5` gives 3 batches and returns 12); `test_stream_file_empty_file_returns_zero`.
- [ ] **Step 2:** Implement `conn.py`/`streaming.py`; run tests; coverage ≥80%.
- [ ] **Step 3:** `modules/databases` RAW schemas and tables; `modules/ingestion` stages, file formats, and Snowpipe Streaming pipe/channel prerequisites (SQL fallback in `sql/` where provider lacks coverage, documented).
- [ ] **Step 4:** `scripts/load-batch` (`PUT` then `COPY INTO`, idempotent via load metadata so a second run loads 0 rows, Review Focus 1); `scripts/stream-load --domain claims`.
- [ ] **Step 5:** Verify live: row counts per domain match generator output; second `load-batch` run reports 0 new rows; guide documents expected counts and cost box (~8 credits).

### Task 7: RBAC, databases and tags

**Files:** Modify `terraform/modules/bootstrap`, `terraform/modules/databases`; create `terraform/modules/governance` (tags part), `docs/guides/02-rbac-and-terraform.md` (completion).
**Interfaces:** Produces schemas `HANBIT_CURATED.<domain>` and `HANBIT_MARTS.<domain>` as managed-access schemas; access roles `<DOMAIN>_RO`/`_RW`; functional roles for the 9 personas (spec §6) mapped by Terraform variable `persona_grants: map(list(string))`; tags `SENSITIVITY` (values `PII, HEALTH, CREDIT, FINANCIAL`) and `DOMAIN`; a tagging step driven from `hanbit_gen.schema.SCHEMAS` sensitivity (generated `tags.auto.tfvars.json`, gitignored output of `scripts/gen-data --emit-tag-map`).

- [ ] **Step 1:** Implement roles/grants with future grants; no direct user grants; `ACCOUNTADMIN` not granted to functional roles.
- [ ] **Step 2:** Verify: `terraform plan` clean after apply; `SHOW GRANTS TO ROLE <persona>` matches a golden file `tests/golden/grants_<persona>.txt` (added as a script check in `scripts/verify-step rbac`).
- [ ] **Step 3:** Guide explains the mapping to IAM groups/roles and Lake Formation/BigQuery policy tags.

### Task 8: Governance policies

**Files:** Modify `terraform/modules/governance`; create `docs/guides/04-governance.md`, `sql/policies_fallback.sql`.
**Interfaces:** Consumes tags from Task 7. Produces masking policies `MASK_PII_STRING`, `MASK_HEALTH`, `MASK_CREDIT_NUMBER`; tag-based attachments on `SENSITIVITY`; row access policy `RAP_REGION_BRANCH` driven by mapping table `GOVERNANCE.ENTITLEMENTS(role_name, region, branch)`; aggregation policy `AGG_MIN_GROUP_5`; projection policy `PROJ_ID_JOINABLE`.

- [ ] **Step 1:** Implement policies in Terraform where supported, otherwise `sql/policies_fallback.sql` run by a bash wrapper; seed the entitlement table from a CSV generated by `gen-data`.
- [ ] **Step 2:** Run auto-classification on RAW (`SYSTEM$CLASSIFY` / classification profile) and compare its suggested tags against the generator's sensitivity map; record gaps in the guide. Verify with Task 9 matrix; verify tag propagation to CURATED after Task 11.
- [ ] **Step 3:** Guide: why tag-based masking scales, entitlement tables as data-not-code, aggregation-policy trade-offs, what Business Critical adds (conceptual only).

### Task 9: Access matrix runner (TDD)

**Files:** Create `src/sfops/matrix.py`, `sql/matrix/access-matrix.yaml`, `scripts/access-matrix`, `tests/test_matrix.py`.
**Interfaces:** `load_matrix(path: Path) -> list[Case]`, `Case(role: str, object: str, column: str | None, expect: Literal["visible","masked","denied","rows"], value: int | None)`; `run_matrix(conn, cases: list[Case]) -> list[Result]`, `Result(case, passed: bool, detail: str)`. Exit code of `scripts/access-matrix` is 1 if any fail. `denied` passes only on Snowflake error codes for insufficient privileges; any other exception propagates as `MatrixInfraError` (Review Focus 5).

- [ ] **Step 1:** Tests with a fake connection: `test_masked_expectation_passes_when_value_is_masked`; `test_denied_passes_on_insufficient_privilege_error_code`; `test_denied_does_not_pass_on_network_error` (raises `MatrixInfraError`); `test_rows_expectation_compares_count`; `test_load_matrix_rejects_unknown_expect_value`.
- [ ] **Step 2:** Implement; use `USE ROLE` per case within one session and restore the role after.
- [ ] **Step 3:** Matrix content: 6 core personas × policy types (spec 14a); stretch cases tagged `stretch: true` and skipped unless `--stretch`.
- [ ] **Step 4:** Verify: unit tests ≥80% coverage; owner runs live, expects all core cases pass; break a policy deliberately once to see a failure and fix it (documented in the guide).

### Task 10: Network, authentication and monitoring

**Files:** Modify `terraform/modules/governance` (network/auth/session policies), create `terraform/modules/monitoring`, `sql/monitoring_views.sql`, section in `docs/guides/07-monitoring-finops-teardown.md`.
**Interfaces:** Produces network policy `NP_HANDSON` (owner's IP supplied via variable, never committed; default allow-list empty and disabled until set), authentication policy requiring MFA for humans and key-pair for service users, views under `HANBIT_OPS.MONITORING` over `COPY_HISTORY`, `PIPE_USAGE_HISTORY`, `DYNAMIC_TABLE_REFRESH_HISTORY`, `TASK_HISTORY`, `LOGIN_HISTORY`, and alerts (pipe failure, DT lag, failed logins, policy changes) sending email to a variable `alert_email` (not committed).

- [ ] **Step 1:** Implement; `plan` shows no lockout risk: a guide warning plus a `--dry-run` preview of the network policy against the owner's current IP before enforcement.
- [ ] **Step 2:** Add `sql/audit.sql` (who read `HEALTH`-tagged columns this week via `ACCESS_HISTORY`, lineage via object dependencies, role grant changes) and a guide section on Trust Center scanners (enable, read findings, fix one).
- [ ] **Step 3:** Verify alerts fire with a deliberate failed pipe load; the audit query returns the matrix test's own reads; confirm cost of monitoring ≤4 credits via `cost-report`.

### Task 11: Transform, pseudonymization, data quality

**Files:** Create `sql/dmf.sql`, transform definitions in `terraform/modules/databases` (Dynamic Tables) or `sql/` fallback, `docs/guides/05-transform-and-iceberg.md` (first half).
**Interfaces:** Consumes RAW tables. Produces `HANBIT_CURATED.<domain>` Dynamic Tables (dedupe, typing, `customer_pseudo_id` as keyed hash), `TARGET_LAG` ≥1 hour, DMFs (null, duplicate, freshness) attached to curated tables.

- [ ] **Step 1:** Implement; verify refresh via `DYNAMIC_TABLE_REFRESH_HISTORY`; suspend DTs after the lab (documented, scripted in `cost-guard`).
- [ ] **Step 2:** Verify masking/row policies still hold on CURATED via Task 9 matrix additions; guide notes lag-versus-cost trade-off with measured credits.

### Task 12: Iceberg v3 and open-engine read

**Files:** Create `sql/iceberg.sql`, `scripts/open-read` (Python via `uv run`, PyIceberg or DuckDB), `docs/guides/05-transform-and-iceberg.md` (second half).
**Interfaces:** Produces Snowflake-managed Iceberg v3 tables `HANBIT_MARTS.CLAIMS_ICEBERG` and `POLICIES_ICEBERG` on Snowflake storage; if preflight says storage is unavailable, produce only the conceptual guide page and the appendix.

- [ ] **Step 1:** Create tables, load via Snowpipe Streaming (Task 6) and CTAS from CURATED; document the unsupported-in-streaming-path items from the docs (no partitioning, no schema evolution).
- [ ] **Step 2:** `scripts/open-read` reads through the Iceberg REST/Horizon catalog with a read-only PAT or key-pair service user and a role limited to masked outputs; it prints row count and demonstrates that policies still apply (or documents honestly where they do not).
- [ ] **Step 3:** Verify counts match Snowflake query; cost box.

### Task 13: BI and AI

**Files:** Create `apps/streamlit/app.py`, `apps/streamlit/environment.yml`, `sql/streamlit.sql`, `sql/semantic_view.sql`, `docs/guides/06-bi-and-ai.md`.
**Interfaces:** Consumes marts. Produces Streamlit app `HANBIT_BI.APP.CLAIMS_OVERVIEW` running as the viewer's role (shows different data per persona), a semantic view `HANBIT_MARTS.CLAIMS_SEMANTIC`, and CoCo usage notes with daily cap set first (`CORTEX_CODE_CLI_DAILY_EST_CREDIT_LIMIT_PER_USER`, value in guide).

- [ ] **Step 1:** Build app pages: claims by region, loss ratio, fraud flags; render per role; `streamlit` import check via `uv run python -c` and `snow streamlit deploy --dry-run` if available.
- [ ] **Step 2:** If preflight says Cortex/CoCo available: semantic view, Cortex Analyst demo and a guided CoCo session (analysis and pipeline task) with the cap set; otherwise guide explains the skip and substitutes the audit deep-dive (spec §14a).
- [ ] **Step 3:** Verify: the same page shows masked values to `MARKETING_ANALYST` and real values to the authorised persona; screenshot-free proof via `access-matrix`.

### Task 14: Cost report, FinOps guide and teardown

**Files:** Create `src/sfops/cost.py`, `tests/test_cost.py`, `scripts/{cost-report,teardown}`, `docs/guides/07-monitoring-finops-teardown.md` (FinOps and teardown).
**Interfaces:** `report(conn, plan: dict[str, float], rate_usd: float) -> list[CostRow]`, `CostRow(area: str, planned: float, actual: float, status: Literal["ok","warn","over"])`; `warn` at ≥80% of planned, `over` above. `scripts/teardown [--dry-run] [--keep-account-objects]` runs `terraform destroy`, drops lab leftovers, suspends monitors, then prints a "still billable" list (storage, Streamlit, DTs, pipes).

- [ ] **Step 1:** Tests: `test_status_thresholds`; `test_dollar_conversion_uses_given_rate` (rate 5.0 vs 4.5 changes dollars, not credits, Review Focus 2); `test_unknown_warehouse_goes_to_other_area`.
- [ ] **Step 2:** Implement reading `METERING_HISTORY` plus Cortex/CoCo usage views (`CORTEX_CODE_CLI_USAGE_HISTORY`), mapping warehouses and services to the plan areas.
- [ ] **Step 3:** Teardown verified twice: second run after a full teardown completes and reports nothing billable (Review Focus 6).
- [ ] **Step 4:** Guide: chargeback by tag/`QUERY_TAG`, budgets, what to do when the trial ends (convert/cancel, billing note).

### Task 15: Claude Code commands and skills

**Files:** Create the six commands and four skills in `.claude/` (see File Structure), `scripts/verify-step`, `.progress/` handling (gitignored).
**Interfaces:** `scripts/verify-step <step>` runs that guide's Verify block (steps `preflight, guardrails, rbac, ingestion, governance, transform, iceberg, bi, finops`) and writes `.progress/state.json` `{step: "ok"|"fail", ts}`. `/sf-next` reads that file and prints the next guide path and its cost box. Commands only wrap scripts; skills encode rules (cost-first, no `ACCOUNTADMIN` for labs, never print secrets, read-only triage for `snowflake-cost-watch`).

- [ ] **Step 1:** Write each command/skill with frontmatter; `snowflake-governance-review` checks RBAC/policies against spec §8 and the repo against §8a.
- [ ] **Step 2:** Verify by invoking each command in dry-run mode; check `verify-step preflight --dry-run` writes nothing.

### Task 16: Appendix, final checks, handoff

**Files:** Create `terraform/modules/appendix_aws_landing`, `docs/guides/appendix-aws.md`; modify `README.md`, `CLAUDE.md`.

- [ ] **Step 1:** Appendix: S3 + KMS + IAM + storage integration + auto-ingest, `terraform validate` only (not applied); states it requires the reader's own AWS account.
- [ ] **Step 2:** Repo-wide grep for stale names (`aws_landing`, "10-day", old script names), broken links between guides, missing "Cost of this step" boxes: all clean.
- [ ] **Step 3:** Run `scripts/check-secrets`, `shellcheck`, `ruff`, `pytest --cov-fail-under=80`, `terraform fmt -check -recursive`, `terraform validate` in every module: all green.
- [ ] **Step 4:** Update `CLAUDE.md` commands and layout to match; propose a GitHub Actions workflow (test, lint, secret scan, terraform validate) and ask the owner before adding. Do not commit unless asked.
