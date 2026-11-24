# Snowflake Hands-On: Insurance & Financing Edition

[日本語版はこちら / Japanese: README.ja.md](README.ja.md)

Learn Snowflake by building a **governed, end-to-end data pipeline** for a fictional insurance and
consumer-lending group, within a **$400 trial budget**. Written for data engineers who already know
AWS, GCP or another cloud, so every Snowflake concept is mapped to something you know.

## What you build
Synthetic source data → ingestion (batch and Snowpipe Streaming) → RAW → curated Dynamic Tables →
Iceberg v3 tables and marts → Streamlit BI and AI, with **column, row and role-level restriction**
proven by an automated access test matrix, plus monitoring, FinOps and a clean teardown.

## 7-day map
| Day | Guide | Focus |
|---|---|---|
| 1 | [00 Orientation](docs/guides/00-orientation.md), [01 Setup](docs/guides/01-setup-and-guardrails.md), [02 RBAC & Terraform](docs/guides/02-rbac-and-terraform.md) | Orientation, guardrails first, RBAC, Terraform, import lab |
| 2 | [03 Ingestion](docs/guides/03-ingestion.md) | Ingestion |
| 3 | [05 Transform & Iceberg](docs/guides/05-transform-and-iceberg.md) (part 1) | Transform to CURATED (policies attach there, so this comes first) |
| 4-5 | [04 Governance](docs/guides/04-governance.md) | Governance: tags, masking, row access, access matrix |
| 5 | [05 Transform & Iceberg](docs/guides/05-transform-and-iceberg.md) (part 2) | Iceberg v3 |
| 6 | [06 BI & AI](docs/guides/06-bi-and-ai.md) | BI and AI |
| 7 | [07 Monitoring & FinOps](docs/guides/07-monitoring-finops-teardown.md) | Monitoring, FinOps, teardown |
| 7+ | [08 CI & apply](docs/guides/08-ci-and-apply.md) | CI and apply from GitHub Actions |
| opt | [Appendix AWS](docs/guides/appendix-aws.md) | Your own S3 bucket |

## Cost
Planned ~53 credits (about $240 at $4.50), reserve ~20, hard stop 80 credits via resource monitor.
Details in [guide 00](docs/guides/00-orientation.md).

## Security baseline
Nothing confidential is ever committed: no account ids, passwords, tokens, keys or Terraform state.
Run `scripts/check-secrets` before every commit. See guide 00.

## Start
`scripts/install-tools && scripts/preflight`, then read guide 01.
