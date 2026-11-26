import re
import runpy
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
LINK = re.compile(r"\]\((?!https?:|#|mailto:)([^)#\s]+)(#[^)]*)?\)")


def test_nav_blocks_are_up_to_date():
    cmd = [sys.executable, str(ROOT / "scripts/sync_doc_nav.py"), "--check"]
    r = subprocess.run(cmd, check=False, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout


def test_every_relative_markdown_link_resolves():
    broken = []
    files = [ROOT / "README.md", ROOT / "README.ja.md", *sorted((ROOT / "docs").glob("**/guides/*.md"))]
    for f in files:
        for m in LINK.finditer(f.read_text()):
            target = (f.parent / m.group(1)).resolve()
            if not target.exists():
                broken.append(f"{f.relative_to(ROOT)} -> {m.group(1)}")
    assert not broken, broken


def test_every_guide_links_back_to_the_day_map_in_both_languages():
    for f in (ROOT / "docs/guides").glob("*.md"):
        assert "README.md#7-day-map" in f.read_text(), f
    for f in (ROOT / "docs/ja/guides").glob("*.md"):
        assert "README.ja.md#7日間の流れ" in f.read_text(), f


def make_tree(tmp_path):
    """A throwaway repo with a copy of the script and every guide reduced to its title."""
    script = tmp_path / "scripts/sync_doc_nav.py"
    script.parent.mkdir()
    shutil.copy(ROOT / "scripts/sync_doc_nav.py", script)
    order = runpy.run_path(str(script))["ORDER"]
    for guides in ("docs/guides", "docs/ja/guides"):
        (tmp_path / guides).mkdir(parents=True)
        for stem in order:
            (tmp_path / guides / f"{stem}.md").write_text("# T\n")
    return script, tmp_path / "docs/guides" / f"{order[0]}.md"


def run_nav(script, *flags):
    cmd = [sys.executable, str(script), *flags]
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


@pytest.mark.parametrize("flags", [[], ["--dry-run"]])
def test_nav_preview_writes_nothing(tmp_path, flags):
    script, guide = make_tree(tmp_path)
    r = run_nav(script, *flags)
    assert r.returncode == 0 and "would update:" in r.stdout
    assert "nothing was changed" in r.stdout and guide.read_text() == "# T\n"


def test_nav_execute_writes(tmp_path):
    script, guide = make_tree(tmp_path)
    r = run_nav(script, "--execute")
    assert r.returncode == 0 and "nothing was changed" not in r.stdout
    assert "<!-- nav:top -->" in guide.read_text()


def test_nav_check_still_fails_on_stale_guides_without_writing(tmp_path):
    script, guide = make_tree(tmp_path)
    r = run_nav(script, "--check")
    assert r.returncode == 1 and "stale:" in r.stdout and guide.read_text() == "# T\n"


@pytest.mark.parametrize(
    "flags", [["--check", "--execute"], ["--dry-run", "--execute"], ["--exceute"]]
)
def test_nav_rejects_bad_flags(tmp_path, flags):
    script, guide = make_tree(tmp_path)
    assert run_nav(script, *flags).returncode == 64 and guide.read_text() == "# T\n"
