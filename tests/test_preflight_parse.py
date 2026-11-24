import pytest

from sfops.preflight import PreflightError, parse_edition, parse_rate, parse_region


@pytest.mark.parametrize("raw,expected", [("4.30", 4.30), ("$4.30", 4.30), (" USD 4.5 ", 4.5), ("3", 3.0)])
def test_parse_rate_accepts_common_inputs(raw, expected):
    assert parse_rate(raw) == expected


@pytest.mark.parametrize("raw", ["", "abc", "-1", "0", "4.5.6"])
def test_parse_rate_rejects_junk_and_non_positive(raw):
    with pytest.raises(PreflightError):
        parse_rate(raw)


def test_parse_edition_from_snow_json_rows():
    raw = '[{"account_name": "X", "edition": "ENTERPRISE"}]'
    assert parse_edition(raw) == "ENTERPRISE"


def test_parse_edition_is_case_insensitive_on_key():
    assert parse_edition('[{"EDITION": "BUSINESS_CRITICAL"}]') == "BUSINESS_CRITICAL"


@pytest.mark.parametrize("raw", ["not json", "[]", '[{"other": 1}]'])
def test_parse_edition_unknown_output_raises(raw):
    with pytest.raises(PreflightError):
        parse_edition(raw)


def test_parse_region_normalises_snowflake_region_id():
    assert parse_region('[{"CURRENT_REGION()": "AWS_AP_NORTHEAST_2"}]') == ("aws", "ap-northeast-2")


def test_parse_region_unknown_raises():
    with pytest.raises(PreflightError):
        parse_region("[]")


def test_cli_edition_reads_stdin_and_prints(monkeypatch, capsys):
    import io

    from sfops.preflight import main

    monkeypatch.setattr("sys.stdin", io.StringIO('[{"edition": "ENTERPRISE"}]'))
    assert main(["edition"]) == 0
    assert capsys.readouterr().out.strip() == "ENTERPRISE"


def test_cli_returns_2_on_unparseable_input(monkeypatch, capsys):
    import io

    from sfops.preflight import main

    monkeypatch.setattr("sys.stdin", io.StringIO("garbage"))
    assert main(["edition"]) == 2
    assert "output is not JSON" in capsys.readouterr().err
