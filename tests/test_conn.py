import logging

import pytest

from sfops import conn as conn_mod
from sfops.conn import ConnectionConfigError, connect, load_profile

TOML = """
[handson_tf]
account = "org-acct"
user = "TERRAFORM"
authenticator = "SNOWFLAKE_JWT"
private_key_file = "/home/u/.snowflake/key.p8"
password = "s3cr3t-value-123"  # fake, test only
"""


@pytest.fixture
def sf_home(tmp_path, monkeypatch):
    monkeypatch.setenv("SNOWFLAKE_HOME", str(tmp_path))
    (tmp_path / "connections.toml").write_text(TOML)
    return tmp_path


def test_missing_file_points_to_bootstrap(tmp_path, monkeypatch):
    monkeypatch.setenv("SNOWFLAKE_HOME", str(tmp_path))
    with pytest.raises(ConnectionConfigError, match="scripts/bootstrap"):
        connect("handson_tf")


def test_missing_entry_raises_config_error(sf_home):
    with pytest.raises(ConnectionConfigError, match="no_such"):
        connect("no_such")


def test_connect_passes_name_and_role(sf_home, monkeypatch):
    seen = {}
    monkeypatch.setattr(conn_mod.snowflake.connector, "connect", lambda **kw: seen.update(kw) or "C")
    assert connect("handson_tf", role="AUDITOR") == "C"
    assert seen == {"connection_name": "handson_tf", "role": "AUDITOR"}


def test_connect_never_logs_or_raises_secret(sf_home, monkeypatch, caplog):
    def boom(**kw):
        raise RuntimeError("login failed")

    monkeypatch.setattr(conn_mod.snowflake.connector, "connect", boom)
    with caplog.at_level(logging.DEBUG), pytest.raises(ConnectionConfigError) as exc:
        connect("handson_tf")
    assert "s3cr3t-value-123" not in caplog.text
    assert "s3cr3t-value-123" not in str(exc.value)


def test_load_profile_returns_only_non_secret_fields(sf_home):
    prof = load_profile("handson_tf")
    assert prof["account"] == "org-acct" and prof["user"] == "TERRAFORM"
    assert "password" not in prof
