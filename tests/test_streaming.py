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
