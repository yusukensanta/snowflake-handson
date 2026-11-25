"""scripts/tf-env turns the CLI profile into the SNOWFLAKE_* variables the Terraform provider reads."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAKE_KEY = "not-a-real-key-body"  # tf-env does not parse the key; avoid PEM markers so check-secrets stays quiet


def _run(home: Path, passphrase: str | None) -> subprocess.CompletedProcess[str]:
    env = {"HOME": str(home), "PATH": "/usr/bin:/bin:/usr/local/bin"}
    if passphrase is not None:
        env["PRIVATE_KEY_PASSPHRASE"] = passphrase
    script = f"source {ROOT}/scripts/tf-env >/dev/null && env"
    return subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True, check=False)


def _profile(home: Path) -> None:
    sf = home / ".snowflake"
    sf.mkdir()
    (sf / "k.p8").write_text(f"{FAKE_KEY}\nsecond line\n")
    (sf / "connections.toml").write_text(
        f'[handson_tf]\naccount = "ORGX-ACCT1"\nuser = "TERRAFORM"\nauthenticator = "SNOWFLAKE_JWT"\n'
        f'private_key_file = "{sf}/k.p8"\nrole = "TF_ADMIN"\n'
    )


def test_exports_provider_variables(tmp_path):
    _profile(tmp_path)
    r = _run(tmp_path, "it's a pass")
    assert r.returncode == 0, r.stderr
    out = r.stdout
    assert "SNOWFLAKE_ORGANIZATION_NAME=ORGX" in out and "SNOWFLAKE_ACCOUNT_NAME=ACCT1" in out
    assert "SNOWFLAKE_USER=TERRAFORM" in out and "SNOWFLAKE_ROLE=TF_ADMIN" in out
    assert "SNOWFLAKE_AUTHENTICATOR=SNOWFLAKE_JWT" in out
    assert "SNOWFLAKE_PRIVATE_KEY_PASSPHRASE=it's a pass" in out  # quoting survives a hostile passphrase
    assert FAKE_KEY in out and "second line" in out  # multi-line key content survives the export


def test_requires_passphrase(tmp_path):
    _profile(tmp_path)
    r = _run(tmp_path, None)
    assert r.returncode != 0 and "PRIVATE_KEY_PASSPHRASE" in r.stderr


def test_missing_profile(tmp_path):
    (tmp_path / ".snowflake").mkdir()
    (tmp_path / ".snowflake" / "connections.toml").write_text("[other]\n")
    r = _run(tmp_path, "x")
    assert r.returncode != 0 and "handson_tf" in r.stderr
