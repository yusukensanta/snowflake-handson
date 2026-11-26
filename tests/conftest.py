"""Sandbox for the shell scripts: copies of scripts/ and sql/, fake external tools, a clean environment."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ("snow", "gh", "uv", "mise", "terraform", "openssl", "shellcheck", "gitleaks")

DEFAULT_BODIES = {
    "snow": r"""case "${@: -1}" in
  "SHOW WAREHOUSES") echo '[{"name":"TRANSFORM_WH","state":"STARTED"}]' ;;
  "SHOW DYNAMIC TABLES"*)
    echo '[{"database_name":"HANBIT_CURATED","schema_name":"CLAIMS","name":"CLAIMS","scheduling_state":"ACTIVE"}]' ;;
  *"COUNT(*) AS N"*) echo '[{"N":0}]' ;;
  *) echo '[]' ;;
esac""",
    "gh": r"""case "$1 $2" in
  "repo view") echo 'o/r' ;;
  "api user") echo 'me' ;;
  "api users/me") echo '1' ;;
esac""",
}


class Sandbox:
    def __init__(self, base: Path) -> None:
        self.repo, self.home = base / "repo", base / "home"
        self._bin, self._log = base / "bin", base / "calls.log"
        ignore = shutil.ignore_patterns("__pycache__")
        shutil.copytree(ROOT / "scripts", self.repo / "scripts", ignore=ignore)
        shutil.copytree(ROOT / "sql", self.repo / "sql")
        (self.repo / "data/out").mkdir(parents=True)
        (self.repo / "data/out/claims.csv.gz").write_bytes(b"x")
        self.home.mkdir()
        self._bin.mkdir()
        for name in TOOLS:
            self.fake(name, DEFAULT_BODIES.get(name, ""))

    def fake(self, name: str, body: str = "") -> None:
        tool = self._bin / name
        tool.write_text(f'#!/usr/bin/env bash\necho "{name} $*" >> "$FAKE_LOG"\n{body}\n')
        tool.chmod(0o755)

    def unfake(self, name: str) -> None:
        (self._bin / name).unlink()

    def run(
        self, script: str, *args: str, env: dict[str, str] | None = None, stdin: str = ""
    ) -> subprocess.CompletedProcess[str]:
        # Built from scratch: no real credential or user-installed tool is reachable.
        child = {"PATH": f"{self._bin}:/usr/bin:/bin", "HOME": str(self.home),
                 "FAKE_LOG": str(self._log), **(env or {})}
        return subprocess.run(
            [str(self.repo / "scripts" / script), *args],
            env=child, input=stdin, capture_output=True, text=True, check=False, timeout=60,
        )

    def calls(self) -> list[str]:
        if not self._log.exists():
            return []
        return [line.rstrip() for line in self._log.read_text().splitlines()]

    def snapshot(self) -> dict[str, bytes]:
        return {
            str(p): p.read_bytes() if p.is_file() else b""
            for root in (self.repo, self.home)
            for p in sorted(root.rglob("*"))
        }


@pytest.fixture
def sandbox(tmp_path: Path) -> Sandbox:
    return Sandbox(tmp_path)
