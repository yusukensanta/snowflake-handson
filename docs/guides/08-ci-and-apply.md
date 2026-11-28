# 08 · CI and apply from GitHub Actions

<!-- nav:top -->
[🏠 7-day map](../../README.md#7-day-map) · ← [07 Monitoring & FinOps](07-monitoring-finops-teardown.md) · [Appendix AWS](appendix-aws.md) →
<!-- /nav:top -->

**Japanese version:** [../ja/guides/08-ci-and-apply.md](../ja/guides/08-ci-and-apply.md)

Business rule: **plan anywhere, apply only from CI after a human approves.** The first apply (guide 02) bootstraps the account from a laptop; once CI is set up, switch to this flow.

> **Check before you start (2026-11-28):** HashiCorp reports an open incident, [Temporary limitations for users on Free Subscription](https://status.hashicorp.com/incidents/01M7XJY4CWY8VQHDC8WFQKEZ47): new free organizations cannot be created (`Free tier organizations created by user limit reached`). If you have no HCP Terraform organization, check the [status page](https://status.hashicorp.com) or contact [HashiCorp Support](https://www.hashicorp.com/support). This guide is optional: the pipeline works without it, and you can go on to teardown ([guide 07](07-monitoring-finops-teardown.md)). An organization in the HCP portal (`portal.cloud.hashicorp.com`) alone may not be visible to Terraform.

## Workflows
| File | Runs | Does |
|---|---|---|
| `.github/workflows/ci.yml` | every PR and push to `main` | `ruff`, `ty`, `pytest` (≥80% coverage), `shellcheck`, `scripts/check-secrets`, `terraform fmt` + `validate` (no credentials needed) |
| `.github/workflows/terraform.yml` | PRs and pushes touching `terraform/**` | PR: `plan` (summary in the job page). `main`: `plan`, then **`apply` after approval** of the `snowflake-apply` environment |

Actions are pinned to commit SHAs, permissions are `contents: read`, and the plan file is never uploaded as an artifact (artifacts of a public repo are world-readable and plans can contain secrets). Fork PRs never receive secrets.

## One-time setup
### Step 1: shared state
Local plan and CI apply must use the same state, so it moves to a free HCP Terraform workspace that only stores it (*Execution mode* **Local**). The steps below follow Terraform 1.17.2 and the HashiCorp docs but **have not been run end to end** (see the notice above). Run them from the repo root, in one shell, and stop at the first failure.

**1a. Baseline and backup, still on local state:**
```bash
read -rs PRIVATE_KEY_PASSPHRASE && export PRIVATE_KEY_PASSPHRASE      # type the passphrase, then Enter
source scripts/tf-env
terraform -chdir=terraform/envs/handson init
terraform -chdir=terraform/envs/handson plan                          # expect: No changes
terraform -chdir=terraform/envs/handson state list | wc -l            # note this number
cp terraform/envs/handson/terraform.tfstate ~/.snowflake/pre-hcp.tfstate
chmod 600 ~/.snowflake/pre-hcp.tfstate                                # state can contain secrets: keep it outside the repo
```

**1b. Create the workspace and migrate.** You need an organization at [app.terraform.io](https://app.terraform.io). Do not use `-migrate-state` (Terraform rejects it for HCP Terraform), and do not rely on `TF_WORKSPACE` to create the workspace: it fails with `Invalid workspace selection`. A `name` in the git-ignored `backend.tf` creates it:
```bash
terraform login
export TF_CLOUD_ORGANIZATION="<your-org>"
export TF_CLOUD_PROJECT="<your-project>"                              # optional; omit for the default project
unset TF_WORKSPACE                                                    # TF_WORKSPACE only selects an existing workspace
cat > terraform/envs/handson/backend.tf <<'EOF'
terraform {
  cloud {
    workspaces {
      name = "snowflake-handson"
    }
  }
}
EOF
terraform -chdir=terraform/envs/handson init                          # answer yes to migrate the state; do not plan yet
```

**1c. Switch the new workspace to Local** through the [workspaces API](https://developer.hashicorp.com/terraform/cloud-docs/api-docs/workspaces) (or *Settings > General > Execution Mode* in the UI). It should print `local`:
```bash
token=$(python3 -c 'import json,pathlib; p=pathlib.Path.home()/".terraform.d/credentials.tfrc.json"; print(json.loads(p.read_text())["credentials"]["app.terraform.io"]["token"])')
printf 'header = "Authorization: Bearer %s"\n' "$token" | curl -sS --fail-with-body -K - \
  -X PATCH -H "Content-Type: application/vnd.api+json" \
  -d '{"data":{"type":"workspaces","attributes":{"execution-mode":"local","setting-overwrites":{"execution-mode":true}}}}' \
  "https://app.terraform.io/api/v2/organizations/$TF_CLOUD_ORGANIZATION/workspaces/snowflake-handson" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["data"]["attributes"]["execution-mode"])'
unset token
```

**1d. Verify:**
```bash
export TF_WORKSPACE=snowflake-handson                                 # the name CI and setup-github use
terraform -chdir=terraform/envs/handson state list | wc -l            # same number as before
terraform -chdir=terraform/envs/handson plan                          # expect: No changes
```
If the count differs or the plan wants to create resources, **do not apply**. CI uses the empty `cloud {}` block from `backend.tf.example` and selects this workspace with `TF_WORKSPACE`.

**Returning to local state** after a failed `init`, before anything was migrated (if the plan then wants to create everything, do not apply; your copy is `~/.snowflake/pre-hcp.tfstate`):
```bash
rm -f terraform/envs/handson/backend.tf
unset TF_CLOUD_ORGANIZATION TF_CLOUD_PROJECT TF_WORKSPACE
source scripts/tf-env
terraform -chdir=terraform/envs/handson init -reconfigure
terraform -chdir=terraform/envs/handson plan                          # expect: No changes
```

### Steps 2 to 5
2. **CI identity.** Give the `TERRAFORM` user a second public key (`ALTER USER TERRAFORM SET RSA_PUBLIC_KEY_2='…'`) generated for CI only, so you can rotate it independently of your laptop key.
3. **GitHub environments** (Settings > Environments): `snowflake-plan` (**required reviewers**: PR code, including edits to the workflow, runs with credentials only after you read it) and `snowflake-apply` (**required reviewers**, deployment branch `main` only). Secrets live on the environments only, and each job reads only its own. Use a **different, read-only Snowflake identity for `snowflake-plan`** (a separate user and a role limited to what refresh needs) and keep the `TF_ADMIN` key only in `snowflake-apply`; set the variable `SNOWFLAKE_ROLE` per environment. Secrets:
   `SNOWFLAKE_ORGANIZATION_NAME`, `SNOWFLAKE_ACCOUNT_NAME`, `SNOWFLAKE_USER`, `SNOWFLAKE_PRIVATE_KEY`, `SNOWFLAKE_PRIVATE_KEY_PASSPHRASE`, `TF_API_TOKEN`, and `TFVARS_JSON` (your private tfvars as JSON; required if they set anything). Variables: `TF_CLOUD_ORGANIZATION`, `TF_WORKSPACE`.
   **This repo does not create a read-only plan identity** (`TERRAFORM_PLAN` / `TF_PLAN` below are example names): create it and its grants yourself. On a throwaway trial account you may instead give both environments `TERRAFORM`, `TF_ADMIN` and the CI key; then an approved PR plan runs with admin rights, so read the whole diff before approving.
4. **Branch protection** on `main`: require the `ci` checks and a pull request.
5. **Network policy:** GitHub-hosted runners have changing IPs. Keep `enforce_account_policies = false` ([guide 07](07-monitoring-finops-teardown.md), section 2). It attaches `NP_HANDSON` to the whole account, which also blocks `TERRAFORM` and the plan user, so CI could not sign in.

## Secrets and variables reference
Everything the workflows read. Nothing here is ever committed; `scripts/setup-github` (below) sets all of it.

| Name | Kind | Scope | What it is and where to get it |
|---|---|---|---|
| `TF_CLOUD_ORGANIZATION` | variable | repo | HCP Terraform organization name (app.terraform.io > Organizations) |
| `TF_WORKSPACE` | variable | repo | Workspace that stores state, *Execution mode = Local* |
| `TF_API_TOKEN` | secret | each environment | HCP Terraform API token that can plan and apply. The Free tier [lists extra teams as unavailable](https://developer.hashicorp.com/terraform/cloud-docs/overview), so use a [user token](https://app.terraform.io/app/settings/tokens) with an expiry. It carries all your permissions; on a paid plan, prefer a team token limited to the workspace |
| `SNOWFLAKE_ORGANIZATION_NAME` | secret | each environment | `SELECT CURRENT_ORGANIZATION_NAME();` |
| `SNOWFLAKE_ACCOUNT_NAME` | secret | each environment | `SELECT CURRENT_ACCOUNT_NAME();` (name only, not the full URL) |
| `SNOWFLAKE_USER` | secret | each environment | `TERRAFORM` for apply; a separate read-only user for plan |
| `SNOWFLAKE_PRIVATE_KEY` | secret | each environment | PEM private key for that user (generate below). Newlines are preserved |
| `SNOWFLAKE_PRIVATE_KEY_PASSPHRASE` | secret | each environment | Passphrase of that key; omit if the key is unencrypted (not recommended) |
| `SNOWFLAKE_ROLE` | variable | each environment | `TF_ADMIN` for apply; the read-only role for plan |
| `TFVARS_JSON` | secret | each environment | **Required if your private `terraform.tfvars` sets anything** (see below). The same settings as JSON |

Account details are secrets, not variables, on purpose: this repo is public and secret values are masked in logs.

### Pass your private settings to CI
CI starts from a clean checkout and never sees your git-ignored `terraform.tfvars`. A setting you leave out falls back to its default, so the plan would **remove** the column tags (guide 04) or the persona grants. Write every setting from your `terraform.tfvars` to `~/.snowflake/tfvars.json` (the tag map is generated by the workflow itself), for example:
```json
{"apply_column_tags": true, "grant_personas_to_user": "<your Snowflake user>"}
```

### Generate a CI-only key pair
```bash
openssl genrsa 2048 | openssl pkcs8 -topk8 -v2 aes-256-cbc -inform PEM -out ~/.snowflake/ci.p8      # asks for a passphrase
openssl rsa -in ~/.snowflake/ci.p8 -pubout -out ~/.snowflake/ci.pub
# register the public key as the SECOND key, so your laptop key keeps working and CI can rotate alone:
#   ALTER USER TERRAFORM SET RSA_PUBLIC_KEY_2='<contents of ci.pub without the BEGIN/END lines>';
```
Use a different key (and user) for plan. Rotate by generating a new key, setting `RSA_PUBLIC_KEY_2`, re-running `scripts/setup-github --execute`, then removing the old key. Delete the local `.p8` files once uploaded if you do not need them.

### Check what is set (names only; GitHub never shows values)
```bash
gh variable list; gh variable list --env snowflake-apply
gh secret list --env snowflake-plan; gh secret list --env snowflake-apply
```

## Scripted setup (steps 3 and 4)
`scripts/setup-github` creates both environments with required reviewers, restricts `snowflake-apply` to `main`, sets the variables and secrets, and optionally protects `main`, all through the GitHub CLI. It is idempotent, so re-run it with `--execute` to rotate a secret. Needs `gh auth login` as a repo admin.
```bash
export TF_CLOUD_ORGANIZATION=… TF_WORKSPACE=… TF_API_TOKEN=…
export PLAN_SNOWFLAKE_USER=TERRAFORM_PLAN  PLAN_SNOWFLAKE_ROLE=TF_PLAN   PLAN_SNOWFLAKE_PRIVATE_KEY_FILE=~/.snowflake/plan.p8
export APPLY_SNOWFLAKE_USER=TERRAFORM      APPLY_SNOWFLAKE_ROLE=TF_ADMIN APPLY_SNOWFLAKE_PRIVATE_KEY_FILE=~/.snowflake/ci.p8
export SNOWFLAKE_ORGANIZATION_NAME=… SNOWFLAKE_ACCOUNT_NAME=…           # shared by both
export TFVARS_JSON_FILE=~/.snowflake/tfvars.json    # your private settings (see above)
# the CI key's passphrase; without it, the laptop one exported by tf-env is uploaded
read -rs APPLY_SNOWFLAKE_PRIVATE_KEY_PASSPHRASE && export APPLY_SNOWFLAKE_PRIVATE_KEY_PASSPHRASE
read -rs PLAN_SNOWFLAKE_PRIVATE_KEY_PASSPHRASE && export PLAN_SNOWFLAKE_PRIVATE_KEY_PASSPHRASE
scripts/setup-github --branch-protection             # preview: prints calls, never values
scripts/setup-github --execute --branch-protection
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

```bash
gh pr checks                                  # on your PR: ci and the terraform plan job are green
gh run list --workflow terraform --limit 3    # after merge: the apply run waits for approval, then completes
```
Open a PR touching a `.tf` file: `ci` is green and the `terraform` workflow shows a plan. After merge, the `apply` job waits for your approval and then reports `Apply complete`. Confirm with `terraform -chdir=terraform/envs/handson plan` (locally, after `source scripts/tf-env`): `No changes`.

---
<!-- nav:bottom -->
[🏠 7-day map](../../README.md#7-day-map) · ← [07 Monitoring & FinOps](07-monitoring-finops-teardown.md) · [Appendix AWS](appendix-aws.md) →
<!-- /nav:bottom -->
