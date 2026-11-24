"""Credit usage report with thresholds matching the budget plan (plan 53, warn 70, hard stop 80)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

PLAN, CRITICAL, HARD_STOP = 53.0, 70.0, 80.0

QUERY = (
    "SELECT SERVICE_TYPE, SUM(CREDITS_USED) FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_HISTORY "
    "WHERE START_TIME >= DATEADD('day', -35, CURRENT_TIMESTAMP()) GROUP BY SERVICE_TYPE ORDER BY 2 DESC"
)


class Status(Enum):
    OK = "OK"
    WARN = "WARN"
    CRITICAL = "CRITICAL"
    STOP = "STOP"


@dataclass(frozen=True)
class CostRow:
    service: str
    credits: float


def evaluate(used: float) -> Status:
    if used >= HARD_STOP:
        return Status.STOP
    if used >= CRITICAL:
        return Status.CRITICAL
    if used >= PLAN:
        return Status.WARN
    return Status.OK


def fetch_rows(conn: Any) -> list[CostRow]:
    rows = conn.cursor().execute(QUERY).fetchall()
    return [CostRow(str(s), float(c or 0.0)) for s, c in rows]


def format_report(rows: list[CostRow]) -> str:
    total = sum(r.credits for r in rows)
    status = evaluate(total)
    lines = [f"{r.service:<28}{r.credits:>10.2f}" for r in rows]
    lines += ["-" * 38, f"{'TOTAL':<28}{total:>10.2f}",
              f"{'REMAINING to hard stop':<28}{HARD_STOP - total:>10.2f}", f"Status: {status.value}"]
    if status is Status.STOP:
        lines.append("Run: scripts/cost-guard --suspend-all")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - live
    import argparse

    from .conn import connect

    p = argparse.ArgumentParser(prog="cost-report")
    p.add_argument("--connection", default="handson_tf")
    a = p.parse_args(argv)
    rows = fetch_rows(connect(a.connection))
    print(format_report(rows))
    return 0 if evaluate(sum(r.credits for r in rows)) in (Status.OK, Status.WARN) else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
