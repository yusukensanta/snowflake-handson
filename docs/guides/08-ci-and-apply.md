# 08 · CI and apply from GitHub Actions

**Japanese version:** [../ja/guides/08-ci-and-apply.md](../ja/guides/08-ci-and-apply.md)

Business rule: **plan anywhere, apply only from CI after a human approves.** The first apply (guide 02) bootstraps the account from a laptop; once CI is set up, switch to this flow.

## Workflows
| File | Runs | Does |
|---|---|---|
| `.github/workflows/ci.yml` | every PR and push to `main` | `ruff`, `ty`, `pytest` (≥80% coverage), `shellcheck`, `scripts/check-secrets`, `terraform fmt` + `validate` (no credentials needed) |
| `.github/workflows/terraform.yml` | PRs and pushes touching `terraform/**` | PR: `plan` (summary in the job page). `main`: `plan`, then **`apply` after approval** of the `snowflake-apply` environment |

Actions are pinned to commit SHAs, permissions are `contents: read`, and the plan file is never uploaded as an artifact (artifacts of a public repo are world-readable and plans can contain secrets). Fork PRs never receive secrets.

## One-time setup
1. **Shared state.** Local plan and CI apply must use the same state. Create a free HCP Terraform organization and a workspace, set its *Execution mode* to **Local** (it only stores state), then locally: `cp terraform/envs/handson/backend.tf.example terraform/envs/handson/backend.tf` (git-ignored), `export TF_CLOUD_ORGANIZATION=… TF_WORKSPACE=…`, `terraform login`, `terraform init -migrate-state`.
2. **CI identity.** Give the `TERRAFORM` user a second public key (`ALTER USER TERRAFORM SET RSA_PUBLIC_KEY_2='…'`) generated for CI only, so you can rotate it independently of your laptop key.
3. **GitHub environments** (Settings > Environments): `snowflake-plan` (**required reviewers**: PR code, including edits to the workflow, runs with credentials only after you read it) and `snowflake-apply` (**required reviewers**, deployment branch `main` only). Secrets live on the environments only, and each job reads only its own. Use a **different, read-only Snowflake identity for `snowflake-plan`** (a separate user and a role limited to what refresh needs) and keep the `TF_ADMIN` key only in `snowflake-apply`; set the variable `SNOWFLAKE_ROLE` per environment. Secrets:
   `SNOWFLAKE_ORGANIZATION_NAME`, `SNOWFLAKE_ACCOUNT_NAME`, `SNOWFLAKE_USER`, `SNOWFLAKE_PRIVATE_KEY`, `SNOWFLAKE_PRIVATE_KEY_PASSPHRASE`, `TF_API_TOKEN`, and optionally `TFVARS_JSON` (the contents of your private tfvars as JSON). Variables: `TF_CLOUD_ORGANIZATION`, `TF_WORKSPACE`.
4. **Branch protection** on `main`: require the `ci` checks and a pull request.
5. **Network policy:** GitHub-hosted runners have changing IPs. Do not enforce `NP_HANDSON` on the `TERRAFORM` user, or CI cannot sign in. Human users stay restricted.

## Scripted setup (steps 3 and 4)
`scripts/setup-github` creates both environments with required reviewers, restricts `snowflake-apply` to `main`, sets the variables and secrets, and optionally protects `main`, all through the GitHub CLI. It is idempotent, so re-run it to rotate a secret. Needs `gh auth login` as a repo admin.
```bash
export TF_CLOUD_ORGANIZATION=… TF_WORKSPACE=… TF_API_TOKEN=…
export PLAN_SNOWFLAKE_USER=TERRAFORM_PLAN  PLAN_SNOWFLAKE_ROLE=TF_PLAN   PLAN_SNOWFLAKE_PRIVATE_KEY_FILE=~/.snowflake/plan.p8
export APPLY_SNOWFLAKE_USER=TERRAFORM      APPLY_SNOWFLAKE_ROLE=TF_ADMIN APPLY_SNOWFLAKE_PRIVATE_KEY_FILE=~/.snowflake/ci.p8
export SNOWFLAKE_ORGANIZATION_NAME=… SNOWFLAKE_ACCOUNT_NAME=…           # shared by both
scripts/setup-github --dry-run --branch-protection   # preview: prints calls, never values
scripts/setup-github --branch-protection
```
Secret values come from your shell and key files and go straight to GitHub; the script never prints or stores them. Self-review is allowed by default (solo owner); add a second reviewer and `--prevent-self-review` for real four-eyes approval. Check the result with `gh api repos/OWNER/REPO/environments --jq '.environments[].name'`.

## Daily flow
```bash
export TF_CLOUD_ORGANIZATION=… TF_WORKSPACE=…
terraform -chdir=terraform/envs/handson plan      # local, read-only against shared state
git switch -c change-x && git commit … && gh pr create
# merge → Actions plans → reviewer approves "snowflake-apply" → apply runs
```
Recovery: if an apply fails halfway, fix forward with a new PR; never edit state by hand from a laptop.

## Cost of this step
0 Snowflake credits for validation. Plan and apply sessions use the metadata services only (a few seconds of cloud services, no warehouse). GitHub Actions minutes are free for public repos.

## Verify
Open a PR touching a `.tf` file: `ci` is green and the `terraform` workflow shows a plan. After merge, the `apply` job waits for your approval and then reports `Apply complete`.
