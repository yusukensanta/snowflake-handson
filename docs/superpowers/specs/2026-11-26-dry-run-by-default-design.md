# Scripts dry-run by default

## Intent
People may run a script without reading its details. A script that changes something must only
preview by default and act only with an explicit `--execute`.

## Goals / non-goals
- Goal: no change to Snowflake, GitHub, the machine or the repo files without `--execute`.
- Goal: read-only checks keep giving real results without a flag.
- Non-goal: guarding direct calls to `terraform`, `snow` or `python -m ...`.
- Anti-goal: a preview that can be mistaken for a completed action.

## Approaches
1. **Flip the default in `scripts/lib/common.sh` (chosen).** One implementation shared by the shell
   scripts; read-only scripts opt out explicitly.
2. A wrapper that adds the safety: calling a script directly would bypass it.
3. A separate flag implementation in each script: duplicated and likely to drift.

## Behaviour

| Script | No flag | `--execute` |
|---|---|---|
| `bootstrap`, `apply-curated`, `apply-policies`, `attach-monitors`, `load-batch`, `stream-load`, `setup-github`, `install-tools`, `gen-data` | preview | act |
| `sync_doc_nav.py` | list files that would change (`--check` unchanged) | write them |
| `teardown` | preview | act, only together with `--yes` |
| `cost-guard --suspend-all` | preview, nothing suspended | suspend |
| `preflight` | read-only checks run; the Iceberg probe is only printed | probe also runs |
| `verify-step` | check runs, progress not recorded | check runs and is recorded |
| `check-secrets`, `access-matrix`, `cost-report`, `cost-guard --status`, `open-read` | run as today | not needed |
| `tf-env` | unchanged | not needed |

- Only the `--execute` argument enables changes. An exported `DRY_RUN=0` does not.
- `--dry-run` stays accepted. Combined with `--execute` it is an error (exit 64).
- A preview ends with a line saying nothing was changed and how to execute.
- Scripts that call other scripts pass `--execute` on explicitly (`teardown` to `cost-guard`).

## Also updated
Guides and README in English and Japanese, `CONTRIBUTING.md`, `CLAUDE.md`, `.claude/commands` and
`.claude/skills`, and every "next step" or "run this" message printed by scripts or `sfops`.

## Verification
Tests run each script against fake `snow`, `gh`, `uv` and install commands and assert that nothing
mutating is called without `--execute`.

## Left to the builder
Helper function names, preview wording and test layout.
