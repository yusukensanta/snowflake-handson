"""Access test matrix: prove column/row/role controls by actually querying as each persona."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml
from snowflake.connector.errors import ProgrammingError

Expect = Literal["visible", "masked", "hashed", "denied", "rows", "regions"]
EXPECTS = {"visible", "masked", "hashed", "denied", "rows", "regions"}
DENIED_ERRNOS = {2003, 3001, 3003}  # object missing/not authorized, insufficient privileges
_IDENT = re.compile(r"^[A-Za-z0-9_]+(\.[A-Za-z0-9_]+)*$")


class MatrixInfraError(RuntimeError):
    """The query failed for a reason that is not a policy outcome (network, missing warehouse...)."""


@dataclass(frozen=True)
class Case:
    role: str
    object: str
    expect: Expect
    column: str | None = None
    value: Any = None
    warehouse: str = "BI_WH"
    sql: str | None = None
    stretch: bool = False


@dataclass(frozen=True)
class Result:
    case: Case
    passed: bool
    detail: str


def load_matrix(path: Path, include_stretch: bool = False) -> list[Case]:
    data = yaml.safe_load(Path(path).read_text())
    cases = []
    for raw in data["cases"]:
        if raw.get("expect") not in EXPECTS:
            raise ValueError(f"bad expect {raw.get('expect')!r}; choose from {sorted(EXPECTS)}")
        case = Case(**raw)
        for ident in (case.role, case.warehouse, case.object, case.column or "x"):
            if not _IDENT.match(ident):
                raise ValueError(f"unsafe identifier {ident!r}")
        if case.stretch and not include_stretch:
            continue
        cases.append(case)
    return cases


def _query(case: Case) -> str:
    if case.sql:
        return case.sql
    if case.expect == "rows":
        return f"SELECT COUNT(*) FROM {case.object}"
    if case.expect == "regions":
        return f"SELECT DISTINCT REGION FROM {case.object}"
    return f"SELECT {case.column} FROM {case.object} LIMIT 1"


def _is_masked(v: Any) -> bool:
    return v is None or (isinstance(v, str) and v.startswith("***"))


def _is_policy_denial(exc: ProgrammingError) -> bool:
    return exc.errno in DENIED_ERRNOS or "policy" in str(exc.msg or exc).lower()


def _evaluate(case: Case, rows: list[tuple]) -> tuple[bool, str]:
    if case.expect in {"visible", "masked", "hashed"}:
        if not rows:
            return False, "no rows returned (a row policy may hide everything)"
        v = rows[0][0]
        if case.expect == "visible":
            return (not _is_masked(v), "value visible" if not _is_masked(v) else f"expected visible, got {v!r}")
        if case.expect == "hashed":
            ok = isinstance(v, str) and re.fullmatch(r"[0-9a-fA-F]{64}", v) is not None
            return ok, "pseudonymised" if ok else f"expected sha256 hex, got {v!r}"
        return (_is_masked(v), "masked" if _is_masked(v) else "leak: expected masked value but saw a real value")
    if case.expect == "denied":
        return False, "query succeeded but access should be denied"
    if case.expect == "rows":
        got = rows[0][0] if rows else None
        return got == case.value, f"row count {got}, expected {case.value}"
    got_set = {r[0] for r in rows}
    return got_set == set(case.value), f"regions {sorted(got_set)}, expected {sorted(case.value)}"


def run_matrix(conn: Any, cases: list[Case]) -> list[Result]:
    cur = conn.cursor()
    original = cur.execute("SELECT CURRENT_ROLE()").fetchone()[0]
    results: list[Result] = []
    try:
        for case in cases:
            cur.execute(f"USE ROLE {case.role}")
            cur.execute("USE SECONDARY ROLES NONE")  # else other roles of the user leak into IS_ROLE_IN_SESSION
            cur.execute(f"USE WAREHOUSE {case.warehouse}")
            try:
                rows = cur.execute(_query(case)).fetchall()
            except ProgrammingError as exc:
                if case.expect == "denied" and _is_policy_denial(exc):
                    results.append(Result(case, True, f"denied (errno {exc.errno})"))
                    continue
                raise MatrixInfraError(f"{case.role} on {case.object}: {exc.msg} (errno {exc.errno})") from exc
            except Exception as exc:
                raise MatrixInfraError(f"{case.role} on {case.object}: {type(exc).__name__}") from exc
            passed, detail = _evaluate(case, rows)
            results.append(Result(case, passed, detail))
    finally:
        cur.execute(f"USE ROLE {original}")
    return results


def main(argv: list[str] | None = None) -> int:
    import argparse

    from .conn import connect

    p = argparse.ArgumentParser(prog="access-matrix")
    p.add_argument("--connection", default="handson_admin", help="human user that holds the persona roles")
    p.add_argument("--matrix", type=Path, default=Path("sql/matrix/access-matrix.yaml"))
    p.add_argument("--stretch", action="store_true")
    a = p.parse_args(argv)
    cases = load_matrix(a.matrix, include_stretch=a.stretch)
    with connect(a.connection) as conn:
        results = run_matrix(conn, cases)
    for r in results:
        print(f"{'PASS' if r.passed else 'FAIL'}  {r.case.role:<24} {r.case.expect:<8} {r.case.object}"
              f"{'.' + r.case.column if r.case.column else ''}  {r.detail}")
    failed = [r for r in results if not r.passed]
    print(f"{len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
