# Contributing

Fixes and improvements to the guides are welcome.

## Ground rules
- **Never commit secrets**: account ids, users, passwords, tokens, keys, state, filled `tfvars`. Run `scripts/check-secrets`.
- **Docs are bilingual**: edit the English guide in `docs/guides/` and its Japanese mirror in `docs/ja/guides/`
  (and `README.md` / `README.ja.md`) in the same pull request. Do not translate code or commands.
  After adding or renaming a guide, update `ORDER`/`LABEL` in `scripts/sync_doc_nav.py` and run
  `uv run python scripts/sync_doc_nav.py`.
- **Every guide ends with a "Cost of this step" box** with credits you actually measured or a clearly marked estimate.
- **Python ships with tests** (80% coverage minimum); data stays synthetic and seeded.
- Scripts are idempotent, accept `--dry-run`, and source `scripts/lib/common.sh`.

## Checks (CI runs the same)
```bash
uv run pytest --cov --cov-fail-under=80
uv run ruff check && uv run ty check src
find scripts tests -type f \( -perm -u+x -o -name "*.sh" \) | xargs shellcheck
terraform -chdir=terraform fmt -check -recursive
scripts/check-secrets
```

Open a pull request against `main`; `terraform apply` never runs from a fork or a local machine.
By contributing you agree your work is released under the [MIT License](LICENSE).
