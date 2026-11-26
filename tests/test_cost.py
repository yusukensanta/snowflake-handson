import pytest

from sfops.cost import CostRow, Status, evaluate, fetch_rows, format_report


class Cur:
    def __init__(self, rows):
        self.rows = rows
        self.sql = None

    def execute(self, sql):
        self.sql = sql
        return self

    def fetchall(self):
        return self.rows


class Conn:
    def __init__(self, rows):
        self.c = Cur(rows)

    def cursor(self):
        return self.c


def test_fetch_rows_maps_tuples_to_costrows_and_handles_null_credits():
    rows = fetch_rows(Conn([("COMPUTE", 1.5), ("SERVERLESS", None)]))
    assert rows == [CostRow("COMPUTE", 1.5), CostRow("SERVERLESS", 0.0)]


@pytest.mark.parametrize("used,expected", [
    (0, Status.OK), (52.9, Status.OK), (53, Status.WARN), (69.9, Status.WARN),
    (70, Status.CRITICAL), (79.9, Status.CRITICAL), (80, Status.STOP),
])
def test_evaluate_thresholds(used, expected):
    assert evaluate(used) is expected


def test_format_report_lists_services_total_and_remaining():
    out = format_report([CostRow("COMPUTE", 10.0), CostRow("AI", 2.5)])
    assert "COMPUTE" in out and "12.50" in out and "67.50" in out and "OK" in out


def test_format_report_flags_stop_and_suggests_guard():
    out = format_report([CostRow("COMPUTE", 81.0)])
    assert "STOP" in out and "cost-guard --suspend-all" in out


def test_stop_report_gives_a_command_that_really_suspends():
    report = format_report([CostRow("X", 81.0)])
    assert "scripts/cost-guard --suspend-all --execute" in report
