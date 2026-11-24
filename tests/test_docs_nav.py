import re
import subprocess
import sys
from pathlib import Path

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
