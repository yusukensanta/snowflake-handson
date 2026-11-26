"""Insert/refresh prev/next + "7-day map" navigation at the top and bottom of every guide (EN and JA).

Reading order is the learning order (05 transform comes before 04 governance), not the file numbering.
Idempotent: blocks live between <!-- nav:top --> / <!-- nav:bottom --> markers.
Previews by default (lists the stale guides); writes only with --execute. --check exits 1 if any guide is stale.
Run: uv run python scripts/sync_doc_nav.py [--execute | --dry-run | --check]
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORDER = ["00-orientation", "01-setup-and-guardrails", "02-rbac-and-terraform", "03-ingestion",
         "05-transform-and-iceberg", "04-governance", "06-bi-and-ai", "07-monitoring-finops-teardown",
         "08-ci-and-apply", "appendix-aws"]
LABEL = {
    "en": ["00 Orientation", "01 Setup", "02 RBAC & Terraform", "03 Ingestion", "05 Transform & Iceberg",
           "04 Governance", "06 BI & AI", "07 Monitoring & FinOps", "08 CI & apply", "Appendix AWS"],
    "ja": ["00 概要", "01 セットアップ", "02 RBAC と Terraform", "03 データ取り込み", "05 変換と Iceberg",
           "04 ガバナンス", "06 BI と AI", "07 監視と FinOps", "08 CI と apply", "付録 AWS"],
}
MAP = {"en": ("../../README.md#7-day-map", "7-day map"), "ja": ("../../../README.ja.md#7日間の流れ", "7日間の流れ")}
DIR = {"en": ROOT / "docs/guides", "ja": ROOT / "docs/ja/guides"}


def block(lang: str, i: int, tag: str) -> str:
    href, name = MAP[lang]
    parts = [f"[🏠 {name}]({href})"]
    if i > 0:
        parts.append(f"← [{LABEL[lang][i - 1]}]({ORDER[i - 1]}.md)")
    if i < len(ORDER) - 1:
        parts.append(f"[{LABEL[lang][i + 1]}]({ORDER[i + 1]}.md) →")
    return f"<!-- nav:{tag} -->\n" + " · ".join(parts) + f"\n<!-- /nav:{tag} -->"


def render(text: str, lang: str, i: int) -> str:
    text = re.sub(r"\n*---\n<!-- nav:bottom -->.*?<!-- /nav:bottom -->\n*", "\n", text, flags=re.DOTALL)
    text = re.sub(r"<!-- nav:top -->.*?<!-- /nav:top -->\n*", "", text, flags=re.DOTALL).rstrip("\n") + "\n"
    head, rest = text.split("\n", 1)  # H1 line
    return f"{head}\n\n{block(lang, i, 'top')}\n{rest.rstrip(chr(10))}\n\n---\n{block(lang, i, 'bottom')}\n"


def main(argv: list[str] | None = None) -> int:
    flags = set(sys.argv[1:] if argv is None else argv)
    unknown = flags - {"--execute", "--dry-run", "--check"}
    if unknown or ("--execute" in flags and len(flags) > 1):
        print("usage: sync_doc_nav.py [--execute | --dry-run | --check]", file=sys.stderr)
        return 64
    check, execute = "--check" in flags, "--execute" in flags
    stale = []
    for lang in ("en", "ja"):
        for i, stem in enumerate(ORDER):
            p = DIR[lang] / f"{stem}.md"
            new = render(p.read_text(), lang, i)
            if new != p.read_text():
                stale.append(p)
                if execute:
                    p.write_text(new)
    label = "stale: " if check else "updated: " if execute else "would update: "
    for p in stale:
        print(label + str(p.relative_to(ROOT)))
    if check:
        return 1 if stale else 0
    if not execute:
        print("[preview] nothing was changed. Re-run with --execute to apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
