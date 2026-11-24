"""Parsers for preflight facts read from `snow sql --format json` output or owner input."""
from __future__ import annotations

import json
import re


class PreflightError(ValueError):
    """Raised when a preflight fact cannot be determined from the given text."""


def parse_rate(raw: str) -> float:
    """Parse a USD-per-credit rate such as '4.30', '$4.30' or 'USD 4.5'."""
    m = re.fullmatch(r"\s*(?:USD|\$)?\s*(\d+(?:\.\d+)?)\s*", raw or "", flags=re.IGNORECASE)
    if not m or float(m.group(1)) <= 0:
        raise PreflightError(f"cannot parse a positive credit rate from {raw!r}")
    return float(m.group(1))


def _rows(raw: str) -> list[dict]:
    try:
        rows = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise PreflightError("output is not JSON") from exc
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
        raise PreflightError("no rows returned")
    return rows


def _first_value(raw: str, key: str) -> str:
    row = _rows(raw)[0]
    for k, v in row.items():
        if k.lower() == key.lower():
            return str(v)
    raise PreflightError(f"column {key!r} missing")


def parse_edition(raw: str) -> str:
    return _first_value(raw, "edition").upper()


def parse_region(raw: str) -> tuple[str, str]:
    """Turn 'AWS_AP_NORTHEAST_2' into ('aws', 'ap-northeast-2')."""
    value = _first_value(raw, "current_region()")
    cloud, _, rest = value.partition("_")
    if not rest:
        raise PreflightError(f"unexpected region id {value!r}")
    return cloud.lower(), rest.lower().replace("_", "-")


def main(argv: list[str]) -> int:
    """CLI used by scripts/preflight: `python -m sfops.preflight rate|edition|region` (stdin)."""
    import sys

    kinds = {
        "rate": lambda s: f"{parse_rate(s):.2f}",
        "edition": parse_edition,
        "region": lambda s: "{}:{}".format(*parse_region(s)),
    }
    if len(argv) != 1 or argv[0] not in kinds:
        print("usage: python -m sfops.preflight rate|edition|region < input", file=sys.stderr)
        return 64
    try:
        print(kinds[argv[0]](sys.stdin.read()))
    except PreflightError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
