"""CLI: python -m hanbit_gen.cli [--rows N] [--out DIR] [--seed N] [--domain D] [--fmt csv|ndjson]
[--emit-tag-map PATH]"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .curated import curated_dynamic_tables_sql, dmf_sql
from .ddl import raw_ddl
from .generator import generate
from .schema import DOMAINS, SCHEMAS


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="gen-data")
    p.add_argument("--rows", type=int, default=200_000)
    p.add_argument("--out", type=Path, default=Path("data/out"))
    p.add_argument("--seed", type=int, default=20261125)
    p.add_argument("--domain", default=None)
    p.add_argument("--fmt", choices=["csv", "ndjson"], default="csv")
    p.add_argument("--emit-tag-map", type=Path, default=None)
    p.add_argument("--emit-ddl", type=Path, default=None)
    p.add_argument("--emit-curated", type=Path, default=None)
    p.add_argument("--emit-dmf", type=Path, default=None)
    a = p.parse_args(argv)
    if a.emit_curated:
        a.emit_curated.write_text(curated_dynamic_tables_sql())
        return 0
    if a.emit_dmf:
        a.emit_dmf.write_text(dmf_sql())
        return 0
    if a.emit_ddl:
        a.emit_ddl.write_text(raw_ddl())
        return 0
    if a.emit_tag_map:
        tags = {f"{d}.{c.name}": c.sensitivity for d in DOMAINS for c in SCHEMAS[d] if c.sensitivity != "none"}
        payload = {"column_sensitivity": tags}  # shape of a *.auto.tfvars.json file
        a.emit_tag_map.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return 0
    if a.domain and a.domain not in SCHEMAS:
        print(f"unknown domain: {a.domain} (choose from {', '.join(DOMAINS)})", file=sys.stderr)
        return 64
    for d in [a.domain] if a.domain else DOMAINS:
        print(generate(d, a.seed, a.rows, a.out, a.fmt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
