# Security policy

This is a tutorial repository. It contains no real credentials and only synthetic data.

## Reporting a problem
- **Leaked secret or personal data in the repo or its history** (account id, key, token, real person's data):
  report it privately through GitHub's "Report a vulnerability" (Security tab) instead of opening a public issue.
- **Insecure pattern taught by a guide** (for example an over-broad grant or a policy that can be bypassed):
  a normal issue or pull request is fine.

## Handling your own secrets when you follow the guides
- Never commit `connections.toml`, `*.p8`/`*.pem` keys, `*.tfvars`, Terraform state or `.env*`; they are git-ignored.
- Run `scripts/check-secrets` before every commit.
- Service users use key-pair authentication; do not use `ACCOUNTADMIN` for routine work.
