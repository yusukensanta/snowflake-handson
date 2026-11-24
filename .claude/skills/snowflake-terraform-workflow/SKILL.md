---
name: snowflake-terraform-workflow
description: Use when editing or applying Terraform under terraform/ in this repo
---
# Terraform workflow
`terraform -chdir=terraform/envs/handson fmt -recursive`, then `validate`, then `plan` and show the plan summary. Apply only with the owner's go-ahead. Provider is pinned (2.23.0); check `terraform providers schema -json` before using a resource. Never commit tfstate or filled tfvars. Resources the provider lacks go in `sql/` with a doc note.
