import pytest
from snowflake.connector.errors import OperationalError, ProgrammingError

from sfops.matrix import Case, MatrixInfraError, load_matrix, run_matrix


class FakeCursor:
    def __init__(self, conn):
        self.conn, self._rows = conn, []

    def execute(self, sql):
        self.conn.executed.append(sql)
        if sql == "SELECT CURRENT_ROLE()":
            self._rows = [("ORIG_ROLE",)]
            return self
        outcome = self.conn.script.get(sql)
        if isinstance(outcome, Exception):
            raise outcome
        self._rows = outcome if outcome is not None else []
        return self

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


class FakeConn:
    def __init__(self, script):
        self.script, self.executed = script, []

    def cursor(self):
        return FakeCursor(self)


def case(**kw):
    base = {"role": "R", "object": "DB.S.T", "column": "C", "expect": "masked"}
    return Case(**{**base, **kw})


Q = "SELECT C FROM DB.S.T LIMIT 1"


def one(conn, c):
    (res,) = run_matrix(conn, [c])
    return res


def test_masked_passes_when_value_is_masked_string():
    assert one(FakeConn({Q: [("***MASKED***",)]}), case()).passed


def test_masked_passes_on_null():
    assert one(FakeConn({Q: [(None,)]}), case()).passed


def test_masked_fails_when_plain_value_leaks():
    res = one(FakeConn({Q: [("900101-1234567",)]}), case())
    assert not res.passed and "leak" in res.detail


def test_visible_passes_on_plain_and_fails_on_masked():
    assert one(FakeConn({Q: [("Seoul",)]}), case(expect="visible")).passed
    assert not one(FakeConn({Q: [("***MASKED***",)]}), case(expect="visible")).passed


def test_visible_fails_loudly_when_row_policy_hides_everything():
    res = one(FakeConn({Q: []}), case(expect="visible"))
    assert not res.passed and "no rows" in res.detail


def test_hashed_passes_on_sha256_hex():
    assert one(FakeConn({Q: [("a" * 64,)]}), case(expect="hashed")).passed


def test_denied_passes_on_insufficient_privilege_code():
    err = ProgrammingError(msg="not authorized", errno=3001)
    assert one(FakeConn({Q: err}), case(expect="denied")).passed


def test_denied_passes_when_message_names_a_policy():
    err = ProgrammingError(msg="Aggregation policy violated", errno=9999)
    assert one(FakeConn({Q: err}), case(expect="denied")).passed


def test_denied_fails_when_query_succeeds():
    assert not one(FakeConn({Q: [("x",)]}), case(expect="denied")).passed


def test_denied_does_not_pass_on_network_error():
    with pytest.raises(MatrixInfraError):
        one(FakeConn({Q: OperationalError(msg="connection reset")}), case(expect="denied"))


def test_denied_does_not_pass_on_unrelated_programming_error():
    with pytest.raises(MatrixInfraError):
        one(FakeConn({Q: ProgrammingError(msg="warehouse missing", errno=606)}), case(expect="denied"))


def test_rows_expectation_compares_count():
    sql = "SELECT COUNT(*) FROM DB.S.T"
    assert one(FakeConn({sql: [(5,)]}), case(expect="rows", column=None, value=5)).passed
    assert not one(FakeConn({sql: [(4,)]}), case(expect="rows", column=None, value=5)).passed


def test_regions_expectation_compares_set():
    sql = "SELECT DISTINCT REGION FROM DB.S.T"
    c = case(expect="regions", column=None, value=["Seoul"])
    assert one(FakeConn({sql: [("Seoul",)]}), c).passed
    assert not one(FakeConn({sql: [("Seoul",), ("Busan",)]}), c).passed


def test_role_and_warehouse_set_per_case_and_role_restored():
    conn = FakeConn({Q: [("***",)]})
    run_matrix(conn, [case(role="CLAIMS_ADJUSTER", warehouse="BI_WH")])
    assert "USE ROLE CLAIMS_ADJUSTER" in conn.executed
    assert "USE WAREHOUSE BI_WH" in conn.executed
    assert conn.executed[-1] == "USE ROLE ORIG_ROLE"
    i = conn.executed.index("USE ROLE CLAIMS_ADJUSTER")
    assert conn.executed[i + 1] == "USE SECONDARY ROLES NONE"


def test_custom_sql_overrides_generated_query():
    conn = FakeConn({"SELECT 1": [(1,)]})
    assert not one(conn, case(expect="denied", column=None, sql="SELECT 1")).passed


def test_load_matrix_rejects_unknown_expect(tmp_path):
    f = tmp_path / "m.yaml"
    f.write_text("cases:\n  - {role: R, object: DB.S.T, column: C, expect: maybe}\n")
    with pytest.raises(ValueError, match="expect"):
        load_matrix(f)


def test_load_matrix_skips_stretch_unless_requested(tmp_path):
    f = tmp_path / "m.yaml"
    f.write_text(
        "cases:\n  - {role: A, object: D.S.T, column: C, expect: masked}\n"
        "  - {role: B, object: D.S.T, column: C, expect: masked, stretch: true}\n"
    )
    assert [c.role for c in load_matrix(f)] == ["A"]
    assert [c.role for c in load_matrix(f, include_stretch=True)] == ["A", "B"]
