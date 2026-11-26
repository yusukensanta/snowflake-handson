"""teardown, preflight and verify-step: scripts that both check and change (runs in a sandbox)."""
import pytest


@pytest.mark.parametrize("args", [(), ("--yes",), ("--dry-run",)])
def test_teardown_previews_without_execute(sandbox, args):
    r = sandbox.run("teardown", *args)
    assert r.returncode == 0 and sandbox.calls() == []
    assert "Re-run with --execute --yes to apply." in r.stdout and "done." not in r.stdout
    assert "cost-guard --execute --suspend-all" in r.stdout


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


def test_verify_step_00_runs_the_secret_scan(sandbox):
    r = sandbox.run("verify-step", "00")
    assert r.returncode == 0, r.stderr
    assert "[check-secrets] clean" in r.stdout


def test_verify_step_execute_records(sandbox):
    sandbox.run("verify-step", "03", "--execute")
    assert '"03"' in (sandbox.repo / ".progress/state.json").read_text()


def test_failed_check_is_not_recorded(sandbox):
    sandbox.fake("snow", "exit 1")
    r = sandbox.run("verify-step", "03", "--execute")
    assert r.returncode != 0 and not (sandbox.repo / ".progress").exists()


def test_verify_step_dry_run_runs_nothing(sandbox):
    r = sandbox.run("verify-step", "03", "--dry-run")
    assert r.returncode == 0 and sandbox.calls() == []
    assert "HANBIT_RAW.CLAIMS.CLAIMS" in r.stdout
