# Dry-run by Default Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scripts that change something only preview by default and act only with `--execute`; read-only checks keep working without a flag.

**Architecture:** `scripts/lib/common.sh` makes preview the default and offers an explicit read-only opt-out. Each script uses those helpers for every side effect and every "it happened" message. Behaviour is proven by running copies of the scripts in a temporary sandbox with fake external tools.

**Tech Stack:** bash, Python 3.15.2 (uv), pytest, shellcheck.

**Spec:** `docs/superpowers/specs/2026-11-26-dry-run-by-default-design.md`

## Global Constraints

- No change to Snowflake, GitHub, the machine or the repo files without `--execute`.
- Only the `--execute` argument enables changes. An exported `DRY_RUN=0` does not.
- `--dry-run` stays accepted. Combined with `--execute` it is an error (exit 64).
- A preview ends with a line saying nothing was changed and how to execute. Exact copy: `[preview] nothing was changed. Re-run with <hint> to apply.` (`<hint>` is `--execute`; `--execute --yes` for `teardown`).
- A preview never prints a message that reads as a completed action.
- Unknown arguments exit 64.
- Scripts stay idempotent, source `scripts/lib/common.sh` (except `tf-env`), and pass shellcheck. `tf-env` is unchanged.
- Docs are bilingual: change `docs/guides` and `docs/ja/guides` (`README.md` and `README.ja.md`) together; never translate commands.
- Do not edit the 2026-11-25 spec and plan (history) or `terraform/` (descriptions there only name scripts, and a `.tf` change would trigger the plan workflow).
- Do not commit or push unless the owner asks. If asked: branch + PR, never `main`.
- During implementation, never run a script with `--execute` in the real repo (it can reach the live account). Only exception: `scripts/gen-data --execute --emit-*` in Task 5, which writes local files.

## Review Focus

1. Old habit `scripts/teardown --yes`: previews, destroys nothing (Task 2).
2. `scripts/check-secrets` given a flag or a typo: never prints `clean` without scanning. Today `check-secrets --dry-run` does exactly that, because the flag is read as the directory (Task 1).
3. `DRY_RUN=0` or `PRINT_ONLY=1` exported in the shell: behaviour is unchanged by it (Task 1).
4. Misspelled `--exceute`: exit 64, nothing runs, including scripts that ignore unknown arguments today (Tasks 1-3).
5. Preview output saying "done", "ready", "generating" or "added": absent (Task 3).

---

### Task 1: Shared flags, test sandbox, read-only scripts and cost-guard

**Files:**
- Modify: `scripts/lib/common.sh`, `scripts/access-matrix`, `scripts/cost-report`, `scripts/open-read`, `scripts/check-secrets`, `scripts/cost-guard`
- Create: `tests/conftest.py`, `tests/test_script_flags.py`
- Modify: `tests/test_cost_guard.py` (pass `--execute`)

**Interfaces:**
- Produces, in `common.sh` (all globals assigned unconditionally, never from the environment):
  - `parse_common_flags "$@"`: sets `DRY_RUN` (1 unless `--execute`), `PRINT_ONLY` (1 only with `--dry-run`), `REST_ARGS`; exits 64 if both flags; installs an EXIT trap that prints the preview line when the exit status is 0 and `DRY_RUN=1`.
  - `mark_read_only`: removes that trap. Read-only code then branches on `PRINT_ONLY`, not `DRY_RUN`.
  - `PREVIEW_HINT` (default `--execute`), read by the trap.
  - `done_msg MSG`: `log_info` only when `DRY_RUN=0`; always returns 0.
  - `run CMD...`: unchanged.
  - `require_cmd` message becomes `(run scripts/install-tools --execute)`.
- Produces, in `conftest.py`: fixture `sandbox` returning an object with
  - `repo: Path`, `home: Path`: copies of `scripts/` and `sql/` plus `data/out/claims.csv.gz` under `tmp_path`
  - `run(script: str, *args: str, env: dict[str, str] | None = None, stdin: str = "") -> subprocess.CompletedProcess[str]`
  - `calls() -> list[str]`: one `"tool arg1 arg2 ..."` per fake-tool invocation
  - `snapshot() -> dict[str, bytes]`: every file and directory under `repo` and `home`, excluding the call log
  - `fake(name: str, body: str = "") -> None`, `unfake(name: str) -> None`
  - Default fakes: `snow gh uv mise terraform openssl shellcheck gitleaks`. `snow` answers `SHOW WAREHOUSES` with one `STARTED` warehouse `TRANSFORM_WH` and `SHOW DYNAMIC TABLES...` with one `ACTIVE` table, a query containing `COUNT(*) AS N` with `[{"N":0}]`, otherwise `[]`. `gh` answers `repo view` with `o/r`, `api user` with `me`, `api users/me` with `1`.
  - The child environment is built from scratch: `PATH=<fakebin>:/usr/bin:/bin`, `HOME`, `FAKE_LOG`, plus `env`. Nothing is inherited, so no real credential or tool is reachable.

- [ ] **Step 1: Write the fixture and failing tests** in `tests/test_script_flags.py`

```python
@pytest.mark.parametrize("script", ["access-matrix", "cost-report", "open-read", "check-secrets", "cost-guard"])
def test_execute_with_dry_run_is_rejected(sandbox, script):
    r = sandbox.run(script, "--execute", "--dry-run")
    assert r.returncode == 64 and sandbox.calls() == []

@pytest.mark.parametrize("args", [(), ("--execute",)])
def test_read_only_scripts_really_run(sandbox, args):
    r = sandbox.run("cost-report", *args)
    assert r.returncode == 0 and "[preview]" not in r.stdout
    assert sandbox.calls() == ["uv run python -m sfops.cost"]

def test_status_runs_without_a_flag(sandbox):
    r = sandbox.run("cost-guard")
    assert any("SHOW RESOURCE MONITORS" in c for c in sandbox.calls()) and "[preview]" not in r.stdout

@pytest.mark.parametrize("env", [{}, {"DRY_RUN": "0"}, {"PRINT_ONLY": "1"}])
def test_suspend_all_previews_whatever_the_environment_says(sandbox, env):
    r = sandbox.run("cost-guard", "--suspend-all", env=env)
    assert r.returncode == 0 and sandbox.calls() == []
    assert "nothing is suspended" in r.stdout
    assert r.stdout.rstrip().endswith("[preview] nothing was changed. Re-run with --execute to apply.")

@pytest.mark.parametrize("arg", ["--dry-run", "--exceute", "/no/such/dir"])
def test_check_secrets_never_reports_clean_without_scanning(sandbox, arg):
    r = sandbox.run("check-secrets", arg)
    assert "clean" not in r.stdout
    assert r.returncode == (0 if arg == "--dry-run" else 64)

def test_check_secrets_still_scans_with_execute(sandbox):
    (sandbox.repo / "leak.txt").write_text("password" + ' = "hunter2hunter2"\n')
    assert sandbox.run("check-secrets", "--execute").returncode == 1

def test_open_read_rejects_unknown_argument(sandbox):
    assert sandbox.run("open-read", "--exceute").returncode == 64 and sandbox.calls() == []
```

In `tests/test_cost_guard.py`, `run_guard` passes `--execute` before `--suspend-all`.

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/test_script_flags.py tests/test_cost_guard.py -q`
Expected: FAIL (for example exit 0 instead of 64; `clean` printed by `check-secrets --dry-run`).

- [ ] **Step 3: Implement the `common.sh` helpers** to the Interfaces above.

- [ ] **Step 4: Convert the scripts**
  - `access-matrix`, `cost-report`, `open-read`: `parse_common_flags` then `mark_read_only`; branch on `PRINT_ONLY`.
  - `open-read`: any remaining argument exits 64.
  - `check-secrets`: source `common.sh`; same two calls. Accept at most one remaining argument, which must not start with `-` and must exist, else exit 64. With `PRINT_ONLY=1` print `[dry-run] would scan <root>` and exit 0.
  - `cost-guard`: `mark_read_only` in status mode, where `show_json` branches on `PRINT_ONLY`. Suspend preview prints `[dry-run] would suspend every started warehouse and active Dynamic Table; nothing is suspended` and exits 0.
  - Update each `Usage:` comment.

- [ ] **Step 5: Verify**

Run: `uv run pytest tests/test_script_flags.py tests/test_cost_guard.py -q && bash tests/test_check_secrets.sh && find scripts tests -type f \( -perm -u+x -o -name "*.sh" \) | xargs shellcheck`
Expected: all pass, `PASS: check-secrets`, no shellcheck output.

---

### Task 2: teardown, preflight, verify-step

**Files:**
- Modify: `scripts/teardown`, `scripts/preflight`, `scripts/verify-step`
- Create: `tests/test_script_mixed.py`

**Interfaces:**
- Consumes: Task 1 helpers and `sandbox`.

- [ ] **Step 1: Write failing tests**

```python
@pytest.mark.parametrize("args", [(), ("--yes",), ("--dry-run",)])
def test_teardown_previews_without_execute(sandbox, args):
    r = sandbox.run("teardown", *args)
    assert r.returncode == 0 and sandbox.calls() == []
    assert "Re-run with --execute --yes to apply." in r.stdout and "done." not in r.stdout

def test_teardown_execute_needs_yes(sandbox):
    assert sandbox.run("teardown", "--execute").returncode == 1 and sandbox.calls() == []

def test_teardown_execute_suspends_then_destroys(sandbox):
    r = sandbox.run("teardown", "--execute", "--yes")
    calls = sandbox.calls()
    assert r.returncode == 0, r.stderr
    suspend = next(i for i, c in enumerate(calls) if "ALTER WAREHOUSE" in c and "SUSPEND" in c)
    destroy = next(i for i, c in enumerate(calls) if c.startswith("terraform") and "destroy" in c)
    assert suspend < destroy and any("DROP ROLE IF EXISTS TF_ADMIN" in c for c in calls)

def test_preflight_default_reads_but_does_not_probe(sandbox):
    r = sandbox.run("preflight", stdin="\n")
    calls = "\n".join(sandbox.calls())
    assert "SELECT CURRENT_REGION()" in calls and "CREATE" not in calls and "DROP" not in calls
    assert "would run: CREATE DATABASE IF NOT EXISTS PREFLIGHT_SCRATCH" in r.stdout

def test_preflight_execute_probes(sandbox):
    sandbox.run("preflight", "--execute", stdin="\n")
    assert any("PREFLIGHT_SCRATCH" in c for c in sandbox.calls())

def test_preflight_dry_run_and_typo_touch_nothing(sandbox):
    assert sandbox.run("preflight", "--dry-run").returncode == 0
    assert sandbox.run("preflight", "--exceute").returncode == 64
    assert sandbox.calls() == []

def test_verify_step_checks_without_recording(sandbox):
    r = sandbox.run("verify-step", "03")
    assert r.returncode == 0 and any("HANBIT_RAW.CLAIMS.CLAIMS" in c for c in sandbox.calls())
    assert not (sandbox.repo / ".progress").exists() and "not recorded" in r.stdout

def test_verify_step_execute_records(sandbox):
    sandbox.run("verify-step", "03", "--execute")
    assert '"03"' in (sandbox.repo / ".progress/state.json").read_text()

def test_failed_check_is_not_recorded(sandbox):
    sandbox.fake("snow", "exit 1")
    r = sandbox.run("verify-step", "03", "--execute")
    assert r.returncode != 0 and not (sandbox.repo / ".progress").exists()

def test_verify_step_dry_run_runs_nothing(sandbox):
    assert sandbox.run("verify-step", "03", "--dry-run").returncode == 0 and sandbox.calls() == []
```

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/test_script_mixed.py -q`
Expected: FAIL (teardown exits 1 without flags; verify-step does not query).

- [ ] **Step 3: Implement**
  - `teardown`: set `PREVIEW_HINT="--execute --yes"`. Refuse (exit 1) only when `DRY_RUN=0` without `--yes`. Call `cost-guard` with `--execute` passed explicitly. Final message through `done_msg`.
  - `preflight`: unknown argument exits 64. `PRINT_ONLY=1` keeps today's list-only branch. Otherwise the read-only checks run; the probe runs only when `DRY_RUN=0`, else print `[dry-run] would run: <probe>` and a row `iceberg-snowflake-storage skip "probe not run; it creates and drops PREFLIGHT_SCRATCH"`. The missing-tool row says `run scripts/install-tools --execute`.
  - `verify-step`: the check runs unless `PRINT_ONLY=1` (then print it). Exit before recording when `DRY_RUN=1`, logging `step <N> check passed; progress not recorded` if it ran.
  - Update each `Usage:` comment.

- [ ] **Step 4: Verify**

Run: `uv run pytest -q && find scripts tests -type f \( -perm -u+x -o -name "*.sh" \) | xargs shellcheck`
Expected: all pass, no shellcheck output.

---

### Task 3: Mutating scripts

**Files:**
- Modify: `scripts/apply-curated`, `apply-policies`, `attach-monitors`, `bootstrap`, `gen-data`, `install-tools`, `load-batch`, `setup-github`, `stream-load`
- Create: `tests/test_script_mutating.py`

**Interfaces:**
- Consumes: Task 1 helpers and `sandbox`.

- [ ] **Step 1: Write failing tests**

```python
CASES = {  # script: (args, substring of a call that proves --execute acted)
    "apply-curated": ((), "curated.sql"),
    "apply-policies": ((), "policies_attach.sql"),
    "attach-monitors": ((), "ALTER WAREHOUSE"),
    "bootstrap": ((), "CREATE RESOURCE MONITOR"),
    "gen-data": (("--rows", "10"), "hanbit_gen.cli --rows 10"),
    "install-tools": ((), "uv tool install snowflake-cli"),
    "load-batch": ((), "COPY INTO"),
    "setup-github": (("--skip-secrets",), "gh api -X PUT"),
    "stream-load": (("--domain", "claims"), "sfops.streaming"),
}
READ_ONLY_GH = ("gh auth status", "gh repo view", "gh api user")

def prepare(sandbox, script):
    if script == "install-tools":
        sandbox.unfake("snow")
    if script == "bootstrap":  # existing key files: --execute needs no real openssl
        (sandbox.home / ".snowflake").mkdir()
        for name in ("handson_tf_key.p8", "handson_tf_key.pub"):
            (sandbox.home / ".snowflake" / name).write_text("x\n")
        (sandbox.home / ".snowflake/connections.toml").write_text("[handson_tf]\n")

@pytest.mark.parametrize("script", CASES)
@pytest.mark.parametrize("flags", [(), ("--dry-run",)])
def test_preview_changes_nothing(sandbox, script, flags):
    prepare(sandbox, script)
    before = sandbox.snapshot()
    r = sandbox.run(script, *CASES[script][0], *flags)
    assert r.returncode == 0, r.stderr
    assert [c for c in sandbox.calls() if not c.startswith(READ_ONLY_GH)] == []
    assert sandbox.snapshot() == before
    assert r.stdout.rstrip().endswith("[preview] nothing was changed. Re-run with --execute to apply.")
    for claim in ("done.", " ready", "generating", "added [", "branch protection on main:"):
        assert claim not in r.stdout

@pytest.mark.parametrize("script", CASES)
def test_execute_acts(sandbox, script):
    prepare(sandbox, script)
    args, proof = CASES[script]
    r = sandbox.run(script, *args, "--execute", env={"PRIVATE_KEY_PASSPHRASE": "x"})
    assert r.returncode == 0, r.stderr
    assert any(proof in c for c in sandbox.calls())
    assert "[preview]" not in r.stdout

def test_fresh_bootstrap_preview_creates_no_files(sandbox):
    assert sandbox.run("bootstrap").returncode == 0
    assert not (sandbox.home / ".snowflake").exists()

def test_setup_github_preview_with_every_option_only_reads(sandbox):
    r = sandbox.run("setup-github", "--branch-protection", env={"TF_API_TOKEN": "not-a-token"})
    assert all(c.startswith(READ_ONLY_GH) for c in sandbox.calls())  # also matches "gh api users/me"
    assert "not-a-token" not in r.stdout

def test_install_tools_rejects_typo(sandbox):
    assert sandbox.run("install-tools", "--exceute").returncode == 64 and sandbox.calls() == []
```

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/test_script_mutating.py -q`
Expected: FAIL (`gen-data` calls `uv` in preview; success messages appear).

- [ ] **Step 3: Implement**
  - All: every end-of-work or success message goes through `done_msg`; every "next step" command in a message carries `--execute` where it changes something; update `Usage:` comments.
  - `gen-data`: source `common.sh`, `parse_common_flags`, then `run uv run python -m hanbit_gen.cli` with `REST_ARGS` (no `exec`, so the preview line can print).
  - `install-tools`: any remaining argument exits 64.
  - `bootstrap`: log "generating..." only when executing; in preview also say it would append `[handson_tf]` to `connections.toml` when absent.
  - `setup-github`: `environment <name> ready`, the branch-protection line and the final line use `done_msg`.
  - `load-batch`: error says `run scripts/gen-data --execute first`.

- [ ] **Step 4: Verify**

Run: `uv run pytest -q && find scripts tests -type f \( -perm -u+x -o -name "*.sh" \) | xargs shellcheck`
Expected: all pass, no shellcheck output.

---

### Task 4: `sync_doc_nav.py`

**Files:**
- Modify: `scripts/sync_doc_nav.py`
- Modify: `tests/test_docs_nav.py`

**Interfaces:**
- Produces: `main(argv: list[str] | None = None) -> int`. No flag or `--dry-run`: print `would update: <path>` per stale file, then the preview line, exit 0. `--execute`: write, print `updated: <path>`. `--check`: unchanged. `--check --execute`, `--dry-run --execute`, or an unknown argument: exit 64.

- [ ] **Step 1: Write failing tests** with a helper that copies the script to `tmp_path/scripts/` and creates every `ORDER` guide in both languages containing only `# T\n`

```python
@pytest.mark.parametrize("flags", [[], ["--dry-run"]])
def test_nav_preview_writes_nothing(tmp_path, flags):
    script, guide = make_tree(tmp_path)
    r = run_nav(script, *flags)
    assert r.returncode == 0 and "would update:" in r.stdout
    assert "nothing was changed" in r.stdout and guide.read_text() == "# T\n"

def test_nav_execute_writes(tmp_path):
    script, guide = make_tree(tmp_path)
    assert run_nav(script, "--execute").returncode == 0
    assert "<!-- nav:top -->" in guide.read_text()

@pytest.mark.parametrize("flags", [["--check", "--execute"], ["--dry-run", "--execute"], ["--exceute"]])
def test_nav_rejects_bad_flags(tmp_path, flags):
    script, guide = make_tree(tmp_path)
    assert run_nav(script, *flags).returncode == 64 and guide.read_text() == "# T\n"
```

- [ ] **Step 2:** Run `uv run pytest tests/test_docs_nav.py -q`. Expected: FAIL (preview writes).
- [ ] **Step 3:** Implement `main` to the interface; update the module docstring.
- [ ] **Step 4:** Run `uv run pytest tests/test_docs_nav.py -q && uv run ruff check`. Expected: pass.

---

### Task 5: Messages from Python and generated headers

**Files:**
- Modify: `src/sfops/cost.py:51`, `src/sfops/conn.py:27,31`, `src/hanbit_gen/ddl.py:8`, `src/hanbit_gen/curated.py:8` (and any other header in that file), `sql/policies_attach.sql` comment
- Regenerate: `sql/raw_tables.sql`, `sql/curated.sql`
- Test: `tests/test_cost.py`

- [ ] **Step 1: Add the failing test** (uses the module's existing imports plus `CostRow`, `format_report`)

```python
def test_stop_report_gives_a_command_that_really_suspends():
    assert "scripts/cost-guard --suspend-all --execute" in format_report([CostRow("X", 81.0)])
```

- [ ] **Step 2:** Run `uv run pytest tests/test_cost.py -q`. Expected: FAIL.
- [ ] **Step 3:** Add `--execute` to each "run this" command: `cost-guard --suspend-all`, `bootstrap`, `gen-data --emit-*`, `apply-policies`. Descriptive mentions of read-only scripts stay.
- [ ] **Step 4:** Regenerate: `scripts/gen-data --execute --emit-ddl sql/raw_tables.sql` and `scripts/gen-data --execute --emit-curated sql/curated.sql`
- [ ] **Step 5:** Run `uv run pytest -q && git diff --stat sql/`. Expected: pass; only comment lines differ in `sql/`.

---

### Task 6: Docs, Claude commands and skills

**Files:**
- Modify: `docs/guides/*.md`, `docs/ja/guides/*.md`, `README.md`, `README.ja.md`, `CONTRIBUTING.md`, `CLAUDE.md`, `SECURITY.md` (only if a mention needs it), `.claude/commands/*.md`, `.claude/skills/*/SKILL.md`
- Create: `tests/test_docs_commands.py`

- [ ] **Step 1: Write the failing tests.** `code_blocks(path) -> list[list[str]]` returns each fenced block's lines starting with `scripts/` (after stripping), comments after ` #` removed.

```python
CHANGES = ("apply-curated", "apply-policies", "attach-monitors", "bootstrap", "gen-data", "install-tools",
           "load-batch", "setup-github", "stream-load", "teardown", "verify-step", "cost-guard --suspend-all")

def test_each_block_that_shows_a_changing_script_shows_how_to_execute_it():
    missing = []
    for f in [*EN_GUIDES, *JA_GUIDES]:
        for block in code_blocks(f):
            for name in CHANGES:
                lines = [c for c in block if re.match(rf"scripts/{re.escape(name)}(\s|$)", c)]
                if lines and not any("--execute" in c.split() for c in lines):
                    missing.append(f"{f.relative_to(ROOT)}: {name}")
    assert not missing, missing

@pytest.mark.parametrize("en", EN_GUIDES, ids=lambda p: p.stem)
def test_japanese_guides_run_the_same_commands(en):
    assert code_blocks(en) == code_blocks(ROOT / "docs/ja/guides" / en.name)
```

- [ ] **Step 2:** Run `uv run pytest tests/test_docs_commands.py -q`. Expected: the first test FAILS. If the parity test fails on pre-existing differences, fix the drift in the same edit.

- [ ] **Step 3: Edit the docs in both languages**
  - Preview lines drop `--dry-run` (bare command); the acting line adds `--execute`. Applies to `install-tools`, `bootstrap`, `load-batch`, `apply-curated`, `setup-github`, `teardown` (`--execute --yes`).
  - Add `--execute` to acting lines with no preview line, and to prose that tells the reader to run or re-run a changing script. Descriptive mentions ("created by `scripts/bootstrap`") stay.
  - Guide 01: `scripts/preflight` first (read-only), then `scripts/preflight --execute` for the Iceberg probe. Verify blocks keep `scripts/preflight`.
  - `verify-step N` becomes `verify-step N --execute`; guide 00 explains that without it the check runs but is not recorded.
  - Guide 00 gains one short paragraph on the rule: preview by default, `--execute` to act, read-only checks need no flag.
  - `access-matrix --dry-run` ("parse only") stays.
  - `CONTRIBUTING.md` and `CLAUDE.md`: new script rule; `sync_doc_nav.py --execute`.
  - `.claude`: `sf-teardown` previews with `scripts/teardown` and runs `--execute --yes` only after explicit confirmation; `sf-verify` and the guide skill use `--execute` to record; `sf-cost` and the cost-watch skill recommend `cost-guard --suspend-all --execute` and ask first; `sf-preflight` stays flagless.

- [ ] **Step 4: Verify everything**

Run:
```bash
uv run pytest --cov --cov-fail-under=80 && uv run ruff check && uv run ty check src
find scripts tests -type f \( -perm -u+x -o -name "*.sh" \) | xargs shellcheck
scripts/check-secrets
grep -rnE -e '--dry-run|teardown --yes' README*.md CONTRIBUTING.md CLAUDE.md docs/guides docs/ja .claude src scripts
```
Expected: tests, lint, types and shellcheck pass; `[check-secrets] clean`; every grep hit is an intentional `--dry-run` support line or `access-matrix --dry-run`.

- [ ] **Step 5: Run real previews** (safe: no `--execute`): `scripts/bootstrap`, `scripts/teardown`, `scripts/cost-guard --suspend-all`, `scripts/gen-data`. Expected: each ends with the preview line and `git status --short` is unchanged.
