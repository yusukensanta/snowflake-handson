# snowflake-handson

Public tutorial repo: governed Snowflake pipeline for a fictional insurance + lending group
("Hanbit Insurance & Capital"). Design: `docs/superpowers/specs/`, plan: `docs/superpowers/plans/`.

## Commands
- Tools: `scripts/install-tools`; checks: `scripts/preflight [--dry-run]`
- Python (uv): `uv run pytest --cov --cov-fail-under=80`, `uv run ruff check`
- Shell: `find scripts tests -type f \( -perm -u+x -o -name "*.sh" \) | xargs shellcheck`; secrets: `scripts/check-secrets`
- Terraform: `terraform -chdir=terraform fmt -check -recursive; terraform -chdir=terraform/envs/handson validate | plan`
- Cost: `scripts/cost-report`, emergency stop: `scripts/cost-guard --suspend-all`

## Rules that matter
- PUBLIC repo: never commit account ids, users, passwords, tokens, keys, tfstate, filled tfvars, connections.toml. Templates are `*.example`. Run `scripts/check-secrets` before any commit.
- Never commit/push unless the owner asks. No CI yet: propose a workflow, ask first.
- Docs are bilingual: English source in `docs/guides/`, Japanese mirror in `docs/ja/guides/` (and `README.ja.md`). Update both in the same change; never translate code/commands.
- Budget: $400 trial, ~88 credits at $4.50; hard stop 80 credits (resource monitor). Every guide ends with a "Cost of this step" box.
- No ACCOUNTADMIN for routine work; service users use key-pair auth.
- Scripts are idempotent, accept `--dry-run`, source `scripts/lib/common.sh`.
- Python ships with tests (>=80% coverage); data is synthetic, seeded, with invalid-check-digit IDs.

## Layout
`docs/guides` (EN) · `docs/ja/guides` (JA) · `terraform/modules,envs` · `sql/` (non-Terraform DDL, access matrix) ·
`src/hanbit_gen` (generator) · `src/sfops` (connection, cost, matrix, streaming) · `scripts/` · `apps/streamlit` · `.claude/{commands,skills}`
