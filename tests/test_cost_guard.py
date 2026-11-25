"""scripts/cost-guard --suspend-all with a fake `snow` on PATH (no Snowflake needed)."""
import os
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FAKE_SNOW = r"""#!/usr/bin/env bash
# args: sql -c CONN [--format json] -q QUERY
conn="$3"; q="${@: -1}"
echo "$conn | $q" >> "$FAKE_LOG"
case "$q" in
  "SHOW WAREHOUSES") echo '[{"name":"TRANSFORM_WH","state":"STARTED"}]' ;;
  "SHOW DYNAMIC TABLES"*) echo '[{"database_name":"HANBIT_CURATED","schema_name":"CLAIMS","name":"CLAIMS","scheduling_state":"ACTIVE"}]' ;;
  "ALTER DYNAMIC TABLE"*) [ "$conn" = "$FAKE_DT_OK_CONN" ] || { echo "Insufficient privileges" >&2; exit 1; } ;;
esac
"""


def run_guard(tmp_path, *args, ok_conn="handson_tf"):
    fake = tmp_path / "snow"
    fake.write_text(FAKE_SNOW)
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    log = tmp_path / "log"
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}", "FAKE_LOG": str(log), "FAKE_DT_OK_CONN": ok_conn}
    r = subprocess.run([str(ROOT / "scripts/cost-guard"), "--suspend-all", *args], env=env, capture_output=True, text=True, check=False)
    return r, log.read_text().splitlines() if log.exists() else []


def test_dynamic_tables_are_suspended_through_the_tf_connection(tmp_path):
    r, calls = run_guard(tmp_path)
    assert r.returncode == 0, r.stderr
    assert "handson_admin | ALTER WAREHOUSE \"TRANSFORM_WH\" SUSPEND" in calls
    assert "handson_tf | ALTER DYNAMIC TABLE HANBIT_CURATED.CLAIMS.CLAIMS SUSPEND" in calls
    assert not any(c.startswith("handson_admin | ALTER DYNAMIC") for c in calls)


def test_dt_connection_can_be_overridden(tmp_path):
    r, calls = run_guard(tmp_path, "--dt-connection", "other", ok_conn="other")
    assert r.returncode == 0, r.stderr
    assert "other | ALTER DYNAMIC TABLE HANBIT_CURATED.CLAIMS.CLAIMS SUSPEND" in calls


def test_failed_suspend_exits_nonzero(tmp_path):
    r, _ = run_guard(tmp_path, "--dt-connection", "handson_admin", ok_conn="nobody")
    assert r.returncode == 1
    assert "incomplete" in r.stderr + r.stdout
