"""Scripts that only make changes: nothing happens without --execute (runs in a sandbox)."""
import pytest

FOOTER = "[preview] nothing was changed. Re-run with --execute to apply."
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
READ_ONLY_GH = ("gh auth status", "gh repo view", "gh api user")  # also matches "gh api users/me"


def prepare(sandbox, script):
    if script == "install-tools":
        sandbox.unfake("snow")
    if script == "bootstrap":  # existing key files: --execute needs no real openssl
        sf = sandbox.home / ".snowflake"
        sf.mkdir()
        for name in ("handson_tf_key.p8", "handson_tf_key.pub"):
            (sf / name).write_text("x\n")
        (sf / "connections.toml").write_text("[handson_tf]\n")


@pytest.mark.parametrize("script", CASES)
@pytest.mark.parametrize("flags", [(), ("--dry-run",)])
def test_preview_changes_nothing(sandbox, script, flags):
    prepare(sandbox, script)
    before = sandbox.snapshot()
    r = sandbox.run(script, *CASES[script][0], *flags)
    assert r.returncode == 0, r.stderr
    assert [c for c in sandbox.calls() if not c.startswith(READ_ONLY_GH)] == []
    assert sandbox.snapshot() == before
    assert r.stdout.rstrip().endswith(FOOTER)
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
    r = sandbox.run("bootstrap")
    assert r.returncode == 0, r.stderr
    assert not (sandbox.home / ".snowflake").exists()
    assert "would append [handson_tf]" in r.stdout


def test_setup_github_preview_with_every_option_only_reads(sandbox):
    r = sandbox.run("setup-github", "--branch-protection", env={"TF_API_TOKEN": "not-a-token"})
    assert r.returncode == 0, r.stderr
    assert all(c.startswith(READ_ONLY_GH) for c in sandbox.calls())
    assert "not-a-token" not in r.stdout


def test_install_tools_rejects_typo(sandbox):
    assert sandbox.run("install-tools", "--exceute").returncode == 64 and sandbox.calls() == []
