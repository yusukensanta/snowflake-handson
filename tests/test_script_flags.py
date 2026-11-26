"""Preview by default: shared flags, the read-only scripts and cost-guard (runs in a sandbox)."""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FOOTER = "[preview] nothing was changed. Re-run with --execute to apply."


@pytest.mark.parametrize(
    "script", ["access-matrix", "cost-report", "open-read", "check-secrets", "cost-guard"]
)
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
    assert any("SHOW RESOURCE MONITORS" in c for c in sandbox.calls())
    assert "[preview]" not in r.stdout


@pytest.mark.parametrize("env", [{}, {"DRY_RUN": "0"}, {"PRINT_ONLY": "1"}])
def test_suspend_all_previews_whatever_the_environment_says(sandbox, env):
    r = sandbox.run("cost-guard", "--suspend-all", env=env)
    assert r.returncode == 0 and sandbox.calls() == []
    assert "nothing is suspended" in r.stdout
    assert r.stdout.rstrip().endswith(FOOTER)


def test_exported_print_only_does_not_silence_a_read_only_script(sandbox):
    sandbox.run("cost-report", env={"PRINT_ONLY": "1"})
    assert sandbox.calls() == ["uv run python -m sfops.cost"]


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


@pytest.mark.parametrize("script", [
    "apply-curated", "apply-policies", "attach-monitors", "bootstrap", "check-secrets", "cost-guard",
    "gen-data", "install-tools", "load-batch", "open-read", "preflight", "setup-github", "stream-load",
    "teardown", "verify-step",
])
@pytest.mark.parametrize("prefix", [(), ("--execute",)])
def test_misspelled_flag_is_rejected_before_anything_runs(sandbox, script, prefix):
    r = sandbox.run(script, *prefix, "--exceute")
    assert r.returncode == 64, r.stdout + r.stderr
    assert sandbox.calls() == []


@pytest.mark.parametrize("args", [("--exceute", "03"), ("03", "--exceute"), ("03", "01")])
def test_verify_step_takes_exactly_one_step(sandbox, args):
    assert sandbox.run("verify-step", *args).returncode == 64 and sandbox.calls() == []


@pytest.mark.parametrize("args", [("--rows", "10", "--exceute"), ("--rows",), ("claims",)])
def test_gen_data_rejects_bad_arguments_in_a_preview(sandbox, args):
    assert sandbox.run("gen-data", *args).returncode == 64 and sandbox.calls() == []


def test_gen_data_accepts_every_option_of_the_generator(sandbox):
    """The shell check duplicates the option list in cli.py; this keeps the two together."""
    cli = (ROOT / "src/hanbit_gen/cli.py").read_text()
    options = re.findall(r'add_argument\("(--[a-z-]+)"', cli)
    assert len(options) >= 9
    for option in options:
        for args in ((option, "x"), (f"{option}=x",)):
            assert sandbox.run("gen-data", *args).returncode == 0, args
    assert sandbox.run("gen-data", "--help").returncode == 0
