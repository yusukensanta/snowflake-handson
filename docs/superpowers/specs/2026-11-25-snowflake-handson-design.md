# Snowflake Hands-On for Data Engineers: Insurance & Financing Edition (Design)

Date: 2026-11-25. Status: draft for approval. Language of all repo content: English.

## 1. Intent and why

The owner has a Snowflake trial (Enterprise, AWS `ap-northeast-2` Seoul, $400 credit, ~2 weeks of 30 days left). They are an experienced data engineer on AWS/GCP who wants to:

1. Learn to build governed end-to-end pipelines on Snowflake.
2. Build and run ELT, visualize the data, and use CoCo (Cortex Code) as an AI agent for analysis and pipeline work.
3. Understand how securely Snowflake provides the platform, and how fine-grained restriction (column, row, role) works when several stakeholders from different domains share it.

The deliverable is a **reusable tutorial repo**: written guides, Terraform, helper scripts, and Claude Code skills/commands. It must work for any cloud-experienced engineer starting Snowflake, not only the owner. The owner is the first user and test subject.

Domain: a **fictional insurance + consumer-finance group ("Hanbit Insurance & Capital")**, chosen because security and governance dominate there. This gives realistic, defensible reasons for every control: PII, health data in claims, credit data in lending, separation of duties, audit.

## 2. Goals, non-goals, anti-goals

**Goals**
- G1. A working pipeline: synthetic source files, S3, Snowflake RAW, Iceberg, curated marts, BI app, AI.
- G2. Governance as the spine, not an add-on: RBAC design, masking, row access, tagging, classification, audit, network/auth policy.
- G3. Everything provisioned by Terraform. One lab teaches `import` of hand-built objects.
- G4. Total spend stays within budget (section 4), enforced by guardrails, not discipline.
- G5. Each guide states what it costs (credits) and how to verify it worked.
- G6. Includes the "why" of each control, in cloud-engineer vocabulary (maps to IAM, KMS, Lake Formation, BigQuery policy tags).

**Non-goals**
- Business Critical features (Tri-Secret Secure, PrivateLink, failover), which are not on this edition. They get a read-only "what changes at the next tier" page.
- Production hardening beyond tutorial scale (multi-account org design, SCIM/SSO setup). SSO and SCIM get a conceptual page only.
- dbt, Airflow, and external orchestrators (optional appendix at most). Snowflake-native tools only.
- Legal or compliance advice. Korean regulations (PIPA, Credit Information Act, Electronic Financial Transactions Act) appear as motivation only, with a disclaimer.

**Anti-goals (failure even if it "works")**
- Any step that can silently burn credits (unsuspended warehouse, runaway Dynamic Table refresh, uncapped AI usage).
- Secrets committed to git, or the tutorial using `ACCOUNTADMIN` for routine work.
- Governance shown only by "trust me" statements. Every control needs a test that proves it as a different role.
- Guides that copy docs instead of teaching mechanisms and trade-offs.

## 3. Constraints

- Trial account, Enterprise edition, AWS Seoul. ~14 days remain; the owner has **7 full free days**, so the plan is **7 working days** with the rest of the trial as buffer. (Superseded the earlier 10-day plan.)
- **No AWS account of the owner's.** The trial's AWS hosting is Snowflake's, and storage is Snowflake-managed, so the core path needs no AWS account, IAM, S3 or SQS. Cloud-integration patterns (storage integration, S3 external stage and volume, Glue catalog) become an optional appendix for readers who have an AWS account, explained conceptually and with Terraform, but not run by the owner.
- **Public repo.** See section 8a.
- Budget $400. Seoul Enterprise credit rate is **not verified** (Tokyo is about $4.30). Plan at **$4.50/credit, so about 88 credits**. A script reads the true rate from the account on day 0.
- Iceberg uses **Snowflake storage** (no external volume). If a reader brings their own S3 external volume, it must be in the account's cloud and region (`ap-northeast-2` here).
- Unverified, to be confirmed by the `preflight` step on day 0, with fallbacks documented:
  - CoCo availability in Seoul and the `CORTEX_ENABLED_CROSS_REGION` requirement (BCR-2376, marked pending). **Owner's decision: if unavailable, skip AI labs and stay in-region.** No cross-region inference is enabled and no new trial is opened. The AI goal then shrinks to local Claude Code plus Snowsight's own features, and the guide explains why.
  - Snowflake-managed Iceberg storage (GA 2026-06-01) in Seoul. This is now on the critical path. If unavailable, Iceberg becomes a conceptual page plus the optional S3 appendix.
  - Terraform provider coverage: Iceberg resources are preview in v2.20.0, so Iceberg objects may need SQL (a `snowflake_execute` resource or SnowCLI) alongside Terraform.
- Machine today: `aws`, `gcloud`, `uv`, `python3` present. `terraform` and `snow` are missing, so the bootstrap script installs them (via mise).
- Repo rules (owner's CLAUDE.md): no commits or pushes unless asked. Application code (the data generator, helper Python) ships with tests at 80% or more coverage. Scripts and config are verified by running them. No CI exists yet, so propose a GitHub Actions workflow later and ask first.

## 4. Cost plan (credits at $4.50 ≈ $400 = 88 credits)

| Area | Assumption | Credits |
|---|---|---|
| Setup, Terraform, DDL, policy tests | XS, about 4 h cumulative, auto-suspend 60 s | 4 |
| Ingestion | Internal-stage batch load and Snowpipe Streaming of about 200 MB synthetic data, plus Iceberg load | 8 |
| Transform | Dynamic Tables with 1 h+ target lag, XS, then suspended | 8 |
| BI | Streamlit in Snowflake, XS, about 8 h of use | 8 |
| Governance | Classification, DMFs, access-history queries, tag propagation | 6 |
| Monitoring | Alerts, tasks, usage views queried by a monitoring warehouse | 4 |
| CoCo/Cortex | Per-user daily cap; Cortex Analyst or Snowflake Intelligence demo | 15 |
| **Planned** | | **~53** |
| Reserve | 22% for mistakes and re-runs | ~20 |
| Hard stop | Account resource monitor SUSPEND_IMMEDIATE at 80 credits | 80 |

- Storage is under 5 GB, so it costs cents. Rounded to $1 for Iceberg metadata, Time Travel and Fail-safe.
- AWS side: $0 for the owner (no AWS resources in the core path).
- Every guide ends with a "Cost of this step" box. The `cost` command compares actual spend with this table.
- CoCo's rate is unknown, so its 15 credits are a conservative placeholder. The daily cap is set before first use. If real spend exceeds plan, CoCo labs shrink first, since they are the optional-depth part.

## 5. Approaches considered

- **A. One capstone company, end to end.** Coherent, and governance falls out of the business story. Chosen.
- **B. Independent labs per topic.** Easy to dip into, but nothing connects and "end to end" is lost.
- **C. Console-first then codify.** Slow, and burns the 2-week window.

Decision (owner): **A**, with one short import lab (build one role by hand, then import it) and the **insurance and financing domain** (this document).

## 6. The scenario

**Company**: Hanbit Insurance & Capital (synthetic, Korean market). Business units become Snowflake domains:

| Domain | Data (synthetic) | Sensitivity |
|---|---|---|
| UNDERWRITING | policies, customers, coverages, premiums | PII (name, RRN-like ID, phone, address) |
| CLAIMS | claims, claim notes, diagnosis codes, payouts | PII plus **health data** (special category) |
| LENDING | loan applications, credit scores, repayments | PII, income, credit info |
| FINANCE | GL, reserves, treasury | Financial, restricted to Finance |
| RISK_FRAUD | fraud flags, model scores | Restricted, joins other domains |
| MARKETING | segments, campaign results | Must see de-identified data only |

**Personas (roles to prove access against)**: claims adjuster (own region, sees diagnosis, masked PII), underwriter (policy PII, no health data), loan officer (own branch, sees credit score, no health data), fraud analyst (cross-domain, pseudonymized IDs), finance controller (finance data, aggregates elsewhere), marketing analyst (aggregates only, k≥5), auditor (read access history, no data), data platform engineer (pipelines, no PII values), security admin (policies, no data). A break-glass role models emergency access with time limit and audit.

## 7. Architecture

```
Synthetic generator (Python, uv)
   -> Batch path:     internal stage (PUT/COPY, encrypted by Snowflake) -> RAW.<domain>
   -> Streaming path: Snowpipe Streaming high-performance Python SDK (key-pair auth)
                      -> RAW.<domain> and Snowflake-managed Iceberg tables
   (optional appendix: S3 + storage integration + Snowpipe auto-ingest, needs own AWS)
   -> Dynamic Tables              -> CURATED.<domain>  (dedupe, typing, pseudonymization)
   -> Snowflake-managed Iceberg v3 tables  -> open-format marts
   -> MARTS (secure views, policies applied via tags)
   -> BI: Streamlit in Snowflake      AI: Cortex Analyst/semantic view, CoCo
   -> Open-engine read of Iceberg (DuckDB/PyIceberg via Iceberg REST) to prove openness
Cross-cutting: tags, masking, row access, aggregation/projection policies,
network policy, auth policies, resource monitors, budgets, alerts, ACCESS_HISTORY
```

Design calls (mine, not the owner's):
- **Snowflake-native transform** (Dynamic Tables). It teaches declarative refresh and lag-versus-cost, with no extra tool to install.
- **Iceberg**: one managed Iceberg table family for curated claims and policies. The goal is to show format openness and the catalog trade-off, not to rebuild everything in Iceberg. External-catalog (Glue) mode is a conceptual page, not a lab.
- **BI**: Streamlit in Snowflake as the primary app because data stays in the account and the owner role's policies apply (owner's rights; corrected 2026-11-27, an earlier draft said it inherits the viewer's role). An optional appendix runs Metabase or Superset locally with a read-only key-pair service user.
- **AI**: Cortex Analyst over a semantic view for business users, and CoCo for the engineer (pipeline authoring, query debugging, governance review). Both run as roles that see only masked data.
- **Data volume**: about 200 MB, deterministic seed, so results are reproducible and cost is predictable.

## 8. Governance and security design (the spine)

1. **RBAC pattern**: object-owner roles, per-schema access roles (`<DOMAIN>_RO`, `_RW`), functional roles for personas, with functional roles granted access roles. Managed access schemas, future grants, no direct grants to users. `ACCOUNTADMIN` is used for bootstrap only (MFA, 2 users, no day-to-day use). `USERADMIN`, `SECURITYADMIN` and `SYSADMIN` separation is taught.
2. **Tags and classification**: sensitivity tags (`PII`, `HEALTH`, `CREDIT`, `FINANCIAL`), auto-classification on RAW, tag propagation downstream via lineage.
3. **Column control**: tag-based masking policies (role- and tag-aware; partial mask, hash pseudonym, full null). `HEALTH` values are visible to the claims role only.
4. **Row control**: row access policies driven by a **mapping table** (role to region/branch), so access is data, not code. A cross-domain entitlement table is the hardest case and is handled explicitly.
5. **Query-shape control**: aggregation policy (marketing, minimum group size) and projection policy (identifier columns usable in joins but never selectable).
6. **Network and identity**: network policy (account and per-service-user), authentication policy (MFA required for humans; key-pair or PAT for service users, no passwords), session policy timeouts, a least-privilege `TERRAFORM` service user.
7. **Encryption and data protection**: what is on by default (encryption at rest and in transit, hierarchical keys), what Enterprise adds (periodic rekeying, longer Time Travel), and what needs Business Critical (explained, not built).
8. **Audit and trust**: `ACCESS_HISTORY` queries ("who saw health columns this week"), `LOGIN_HISTORY`, Trust Center scanners, object dependencies and lineage, data quality via Data Metric Functions.
9. **Proof**: an automated **access test matrix** (persona × table × column × expected result) executed with `USE SECONDARY ROLES`/`EXECUTE AS`-style role switching, written as a repeatable script. A failing matrix fails the lab.

## 8a. Public-repo security baseline (the tutorial models what it teaches)

- **Nothing confidential is committed**: no account identifier, user names, passwords, tokens, private keys, PATs, `terraform.tfstate`, `*.tfvars` with values, or `connections.toml`. Committed templates use placeholders (`*.example`).
- `.gitignore` covers state, keys, `.env`, tfvars and local config from the first commit. A **secret scan** (gitleaks pre-commit hook plus a script `scripts/check-secrets`) blocks it. CI later runs the same scan, once the owner approves adding a workflow.
- **Credentials**: key-pair auth for service users (keys generated locally under `~/.snowflake/`, passphrase-protected, never in the repo). Human users use MFA. No passwords in scripts. Terraform reads credentials from environment variables or the Snowflake config file only.
- **Synthetic data only**, generated with a fixed seed; identifiers such as RRN-like IDs are obviously fake (invalid check digit) so they cannot match real people.
- **Terraform state** holds sensitive values, so it stays local and ignored, and the S3-backend lab shows an encrypted, versioned, private backend instead.
- The guides state the minimum security bar for each step and why, and the `snowflake-governance-review` skill checks the repo itself against this baseline.

## 9. Terraform scope

- Provider `snowflakedb/snowflake` (version pinned after checking the latest on day 0; v2.x resources use the new naming). Auth by key-pair for a dedicated `TERRAFORM` user, never the owner's password.
- State: local backend with an optional S3 backend lab (versioned, encrypted bucket in Seoul).
- Modules: `bootstrap` (roles, user, warehouses, monitors), `databases` (db, schemas, grants), `governance` (tags, policies, attachments), `ingestion` (internal stage, pipes, streaming channel setup), `appendix_aws_landing` (optional: S3, KMS, IAM, storage integration; not applied by the owner), `monitoring` (alerts, tasks), `finops` (monitors, budgets).
- Gaps covered with SQL (SnowCLI) and documented in-line: Iceberg tables if the provider is still preview, Streamlit, semantic views, DMF attachments where unsupported.
- **Import lab**: create one role and one warehouse by hand, write the config, use `import` blocks, then converge the plan to no-op. It includes the drift-detection discussion.

## 10. Monitoring and FinOps

- **Platform and pipeline monitoring**: views over `ACCOUNT_USAGE`/`INFORMATION_SCHEMA` for `COPY_HISTORY`, `PIPE_USAGE_HISTORY`, `DYNAMIC_TABLE_REFRESH_HISTORY`, `TASK_HISTORY`, `QUERY_HISTORY`; email alerts on pipe failure, DT lag, failed logins, and policy changes. A monitoring Streamlit page. Event tables and logging are covered briefly.
- **FinOps**: account resource monitor (notify 50/75/90, suspend at 100 of the 80-credit hard stop); per-warehouse monitors; budgets; `AUTO_SUSPEND` 60 s; `STATEMENT_TIMEOUT`; cost tags and `QUERY_TAG` for chargeback by domain; a CoCo daily credit cap; a `cost` command reporting actual versus planned per area.

## 11. Helper scripts and Claude Code assets

**Repo layout**
```
CLAUDE.md                 commands, layout, conventions (under 100 lines)
README.md                 start here, 7-day map, cost box
docs/guides/00..NN-*.md   one guide per step (setup ... teardown)
docs/superpowers/specs/   this design
terraform/modules/*, terraform/envs/handson/
sql/                      non-Terraform DDL, access-test matrix
data/generator/           Python (uv), pytest, 80% or more coverage
scripts/                  bash and python helpers
.claude/commands/         slash commands
.claude/skills/           skills
```

**Scripts** (`scripts/`): `preflight` (tools, versions, account edition/region, credit rate, CoCo/Iceberg/cross-region checks), `install-tools` (terraform, snow via mise), `bootstrap` (keypair, `TERRAFORM` user and role, `connections.toml`, minimal admin SQL), `gen-data`, `upload-data`, `access-matrix` (runs persona tests), `cost-report` (actual versus planned), `cost-guard` (suspend warehouses and monitors, emergency stop), `teardown` (destroy and verify nothing billable remains).

**Commands** (`.claude/commands/`): `/sf-preflight`, `/sf-next` (which guide step is next, from a progress file), `/sf-cost`, `/sf-verify <step>` (runs that step's checks), `/sf-access-test`, `/sf-teardown`.
**Skills** (`.claude/skills/`): `snowflake-handson-guide` (how to drive the tutorial, the cost-first rule, never use ACCOUNTADMIN for labs), `snowflake-governance-review` (review RBAC and policies against section 8), `snowflake-cost-watch` (read-only cost triage), `snowflake-terraform-workflow` (plan, import, and drift rules).

## 12. 7-day schedule (full days)

| Day | Content | Credits |
|---|---|---|
| 1 | Preflight, tools, resource monitor and budget first, RBAC and Terraform bootstrap, import lab | 4 |
| 2 | Data generator, internal-stage batch ingest into RAW, Snowpipe Streaming, monitoring v1 | 8 |
| 3 | Tags, classification, masking policies, row access policies | 7 |
| 4 | Aggregation and projection policies, access matrix, network and authentication policies | 3 |
| 5 | Dynamic Tables to CURATED, pseudonymization, DMFs, Iceberg v3 tables, open-engine read | 14 |
| 6 | Streamlit BI, Cortex Analyst and CoCo (if available in Seoul, otherwise audit and Trust Center deep-dive) | 14 |
| 7 | Audit and Trust Center, FinOps review, monitoring v2, teardown | 3 |

Total about 53 credits, matching section 4. Spare trial days and the ~20-credit reserve absorb re-runs. If a feature is unavailable in Seoul, swap in the cut order from 14a.

## 13. Verification and quality

- Python: pytest at 80% or more; `ruff` and type check.
- Shell: `shellcheck`/`bash -n`; every script has `--dry-run`.
- Terraform: `fmt`, `validate`, `plan` in a clean state. Apply is verified on the owner's live account.
- The access test matrix is the proof of governance. The `cost-report` is the proof of budget.
- A repo-wide grep for stale names at the end of each change.
- Guides are run by the owner step by step, and fixes feed back into the guides.

## 14. Risks

| Risk | Mitigation |
|---|---|
| Real Seoul rate above $4.50 | Day 0 reads the real rate; the budget table is rescaled |
| CoCo or Cortex unavailable in Seoul | Preflight; cross-region inference setting; the CoCo labs fall back to Snowsight and local Claude Code |
| Iceberg Terraform resources are preview | SQL fallback in-line |
| Trial ends before finishing | 7 free days fit well inside the ~14 left; governance first, appendices last |
| Secrets leak into the public repo | Section 8a: ignore rules, templates only, secret scan before any commit |
| Billing after trial end | `teardown` plus a note on trial-to-paid conversion; set the monitor and remove the payment method if unwanted |
| Provider and doc drift | Versions pinned; each guide lists the doc links it relied on and the verification date |

## 14a. Calls made after the builder check (mine; the owner can overrule)

- **Who runs it**: the owner runs the guides by hand. Scripts are non-interactive, idempotent and have `--dry-run`. Claude commands only wrap them, and nothing requires an agent to drive.
- **Access matrix**: core of 6 personas (claims adjuster, underwriter, loan officer, marketing analyst, auditor, platform engineer) tested on all policy types. The other three personas and the cross-domain entitlement case are stretch, run only if day 5 stays under budget.
- **Cut order if the real credit rate is high or time runs short**: (1) CoCo/Cortex depth, (2) Streamlit extras and monitoring v2, (3) the open-engine read, (4) the Iceberg lab, in that order. Never cut: RBAC, Terraform, ingestion, masking/row policies, the access matrix, cost guardrails, teardown.

## 15. Left to the builder

Exact object names, column lists and generator schema; exact Terraform resource spellings per pinned provider version; guide wording and diagrams; Streamlit layout; exact alert thresholds.
