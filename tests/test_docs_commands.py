"""The commands in the guides: changing scripts are shown with --execute, in both languages alike."""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EN_GUIDES = sorted((ROOT / "docs/guides").glob("*.md"))
JA_GUIDES = sorted((ROOT / "docs/ja/guides").glob("*.md"))
CHANGES = (
    "apply-curated", "apply-policies", "attach-monitors", "bootstrap", "gen-data", "install-tools",
    "load-batch", "setup-github", "stream-load", "teardown", "verify-step", "cost-guard --suspend-all",
)
FENCE = re.compile(r"^```[^\n]*\n(.*?)^```", re.MULTILINE | re.DOTALL)


def code_blocks(path: Path) -> list[list[str]]:
    """Per fenced block, the lines that run a script, without trailing comments."""
    return [
        [line.strip().split(" #")[0].rstrip()
         for line in body.splitlines() if line.strip().startswith("scripts/")]
        for body in FENCE.findall(path.read_text())
    ]


def test_each_block_that_shows_a_changing_script_shows_how_to_execute_it():
    missing = []
    for f in [*EN_GUIDES, *JA_GUIDES]:
        for block in code_blocks(f):
            for name in CHANGES:
                lines = [c for c in block if re.match(rf"scripts/{re.escape(name)}(\s|$)", c)]
                if lines and not any("--execute" in c.split() for c in lines):
                    missing.append(f"{f.relative_to(ROOT)}: {name}")
    assert not missing, missing


@pytest.mark.parametrize("en", EN_GUIDES, ids=lambda p: p.stem)
def test_japanese_guides_run_the_same_commands(en):
    assert code_blocks(en) == code_blocks(ROOT / "docs/ja/guides" / en.name)
