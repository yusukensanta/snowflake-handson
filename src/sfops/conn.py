"""Snowflake connection helper. Reads ~/.snowflake/connections.toml (or $SNOWFLAKE_HOME)."""
from __future__ import annotations

import logging
import os
import tomllib
from pathlib import Path

import snowflake.connector

log = logging.getLogger(__name__)

_SECRET_KEYS = {"password", "token", "private_key", "private_key_passphrase", "passcode"}


class ConnectionConfigError(RuntimeError):
    """Connection entry missing or unusable. Messages never contain credential values."""


def _config_path() -> Path:
    return Path(os.environ.get("SNOWFLAKE_HOME", Path.home() / ".snowflake")) / "connections.toml"


def _entry(name: str) -> dict:
    path = _config_path()
    if not path.exists():
        raise ConnectionConfigError(f"{path} not found; create it (guide 01) or run scripts/bootstrap")
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    if name not in data:
        raise ConnectionConfigError(f"connection '{name}' not in {path}; run scripts/bootstrap")
    return data[name]


def load_profile(name: str) -> dict[str, str]:
    """Non-secret connection fields (account, user, role, key file path) for SDK adapters."""
    return {k: str(v) for k, v in _entry(name).items() if k not in _SECRET_KEYS}


def connect(connection_name: str, role: str | None = None) -> snowflake.connector.SnowflakeConnection:
    _entry(connection_name)  # validates presence
    kwargs: dict[str, str] = {"connection_name": connection_name}
    if role:
        kwargs["role"] = role
    try:
        return snowflake.connector.connect(**kwargs)
    except Exception as exc:  # noqa: BLE001 - never forward driver text: it may echo parameters
        log.error("could not connect using '%s' (%s)", connection_name, type(exc).__name__)
        raise ConnectionConfigError(
            f"could not connect using '{connection_name}' ({type(exc).__name__}); check key, passphrase and role"
        ) from None
