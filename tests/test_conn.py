import logging
import uuid

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
    with pytest.raises(ConnectionConfigError, match="scripts/bootstrap --execute"):
        connect("handson_tf")


def test_missing_entry_raises_config_error(sf_home):
    with pytest.raises(ConnectionConfigError, match="no_such"):
        connect("no_such")


def test_connect_passes_name_and_role(sf_home, monkeypatch):
    seen = {}
    monkeypatch.setattr(conn_mod.snowflake.connector, "connect", lambda **kw: seen.update(kw) or "C")
    assert connect("handson_tf", role="AUDITOR") == "C"
    assert seen == {
        "connection_name": "handson_tf",
        "role": "AUDITOR",
        "enable_server_session_keep_alive_auto_detection": False,
    }


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


def test_connect_expands_tilde_in_private_key_file(tmp_path, monkeypatch):
    # The connector's Rust core does not expand "~"; passing it through gives "No such file".
    monkeypatch.setenv("SNOWFLAKE_HOME", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / "connections.toml").write_text(
        '[h]\naccount = "a-b"\nuser = "U"\nprivate_key_file = "~/.snowflake/k.p8"\n'
    )
    seen = {}
    monkeypatch.setattr(conn_mod.snowflake.connector, "connect", lambda **kw: seen.update(kw) or "C")
    connect("h")
    assert seen["private_key_file"] == str(tmp_path / ".snowflake" / "k.p8")


def test_connect_leaves_absolute_key_path_alone(sf_home, monkeypatch):
    seen = {}
    monkeypatch.setattr(conn_mod.snowflake.connector, "connect", lambda **kw: seen.update(kw) or "C")
    connect("handson_tf")
    assert "private_key_file" not in seen


def test_connect_maps_passphrase_env_to_connector_param(sf_home, monkeypatch):
    value = uuid.uuid4().hex  # generated, so no password-like literal sits in the repo
    monkeypatch.setenv("PRIVATE_KEY_PASSPHRASE", value)
    seen = {}
    monkeypatch.setattr(conn_mod.snowflake.connector, "connect", lambda **kw: seen.update(kw) or "C")
    connect("handson_tf")
    assert seen["private_key_password"] == value


def test_connect_without_passphrase_env_passes_none(sf_home, monkeypatch):
    monkeypatch.delenv("PRIVATE_KEY_PASSPHRASE", raising=False)
    seen = {}
    monkeypatch.setattr(conn_mod.snowflake.connector, "connect", lambda **kw: seen.update(kw) or "C")
    connect("handson_tf")
    assert "private_key_password" not in seen
