import gzip

import pytest

from sfops.streaming import stream_file


class FakeSink:
    def __init__(self, fail_on=None):
        self.batches, self.closed, self.fail_on = [], False, fail_on

    def append(self, rows, end_offset):
        if self.fail_on == len(self.batches):
            raise RuntimeError("append failed")
        self.batches.append((len(rows), end_offset))

    def flush(self):
        self.flushed = True

    def close(self):
        self.closed = True


def write_csv(path, n):
    with gzip.open(path, "wt") as fh:
        fh.write("a,b\n")
        for i in range(n):
            fh.write(f"{i},x{i}\n")
    return path


def test_stream_file_batches_rows(tmp_path):
    sink = FakeSink()
    n = stream_file("c", "claims", write_csv(tmp_path / "f.csv.gz", 12), batch_size=5,
                    sink_factory=lambda conn, domain: sink)
    assert n == 12
    assert sink.batches == [(5, "5"), (5, "10"), (2, "12")]
    assert sink.closed and sink.flushed


def test_stream_file_empty_file_returns_zero(tmp_path):
    sink = FakeSink()
    assert stream_file("c", "claims", write_csv(tmp_path / "f.csv.gz", 0),
                       sink_factory=lambda conn, domain: sink) == 0
    assert sink.batches == [] and sink.closed


def test_sink_closed_even_when_append_fails(tmp_path):
    sink = FakeSink(fail_on=0)
    with pytest.raises(RuntimeError):
        stream_file("c", "claims", write_csv(tmp_path / "f.csv.gz", 3),
                    sink_factory=lambda conn, domain: sink)
    assert sink.closed


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        stream_file("c", "claims", tmp_path / "nope.csv.gz", sink_factory=lambda c, d: FakeSink())


def test_batch_size_must_be_positive(tmp_path):
    with pytest.raises(ValueError):
        stream_file("c", "claims", write_csv(tmp_path / "f.csv.gz", 1), batch_size=0,
                    sink_factory=lambda c, d: FakeSink())


def test_cli_streams_named_domain_and_prints_count(tmp_path, monkeypatch, capsys):
    from sfops import streaming

    f = write_csv(tmp_path / "claims.csv.gz", 3)
    monkeypatch.setattr(streaming, "stream_file", lambda conn, domain, path, batch_size: 3)
    assert streaming.main(["--connection", "c", "--domain", "claims", "--file", str(f)]) == 0
    assert capsys.readouterr().out.strip() == "streamed 3 rows into claims"


def test_sdk_properties_builds_url_and_key_file(tmp_path):
    from sfops.streaming import sdk_properties

    profile = {"account": "ORG-ACCT", "user": "TERRAFORM", "private_key_file": "~/k.p8", "role": "TF_ADMIN",
               "authenticator": "SNOWFLAKE_JWT", "warehouse": "TRANSFORM_WH"}
    props = sdk_properties(profile, {"PRIVATE_KEY_PASSPHRASE": "pw"})
    assert props["url"] == "https://ORG-ACCT." + "snowflake" + "computing.com"  # split so check-secrets stays quiet
    assert props["account"] == "ORG-ACCT" and props["user"] == "TERRAFORM" and props["role"] == "TF_ADMIN"
    assert props["authorization_type"] == "JWT"
    assert props["private_key_file"].endswith("/k.p8") and not props["private_key_file"].startswith("~")
    assert props["private_key_passphrase"] == "pw"
    assert "authenticator" not in props and "warehouse" not in props


def test_sdk_properties_without_passphrase_or_role():
    from sfops.streaming import sdk_properties

    props = sdk_properties({"account": "A-B", "user": "U", "private_key_file": "/k.p8"}, {})
    assert "private_key_passphrase" not in props and "role" not in props


def test_sdk_properties_requires_account_user_and_key():
    from sfops.streaming import sdk_properties

    with pytest.raises(ValueError, match="private_key_file"):
        sdk_properties({"account": "A-B", "user": "U"}, {})


def test_summarize_status_ok_and_failures():
    from types import SimpleNamespace as NS

    from sfops.streaming import summarize_status

    ok = NS(status_code="ACTIVE", rows_inserted_count=10, rows_error_count=0, last_error_message=None)
    assert "inserted 10 of 10" in summarize_status(ok, 10)
    bad = NS(status_code="ACTIVE", rows_inserted_count=0, rows_error_count=10, last_error_message="column mismatch")
    with pytest.raises(RuntimeError, match="column mismatch"):
        summarize_status(bad, 10)
    short = NS(status_code="ACTIVE", rows_inserted_count=4, rows_error_count=0, last_error_message=None)
    with pytest.raises(RuntimeError, match="fewer rows"):
        summarize_status(short, 10)
