"""Stream a generated .csv.gz file into Snowflake with the Snowpipe Streaming high-performance SDK.

The SDK is imported lazily so unit tests and `uv sync` do not need it
(`uv sync --extra streaming` installs snowpipe-streaming).
"""
from __future__ import annotations

import csv
import gzip
import io
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Protocol

from .conn import load_profile


class RowSink(Protocol):
    def append(self, rows: list[dict], end_offset: str) -> None: ...
    def flush(self) -> None: ...
    def close(self) -> None: ...


class SdkSink:  # pragma: no cover - needs the real SDK and a live account; verified by the owner
    """Adapter over snowflake.ingest.streaming (table mode: pipe is `<TABLE>-STREAMING`)."""

    def __init__(self, conn_name: str, domain: str, database: str = "HANBIT_RAW") -> None:
        from snowflake.ingest.streaming import StreamingIngestClient  # ty: ignore[import-not-found]  # optional extra "streaming"

        profile = load_profile(conn_name)
        self._client = StreamingIngestClient.from_table(
            f"handson-{domain}", database, domain.upper(), f"{domain.upper()}_STREAM",
            properties=profile,
        )
        self._channel, _ = self._client.open_channel(f"{domain}_channel")

    def append(self, rows: list[dict], end_offset: str) -> None:
        self._channel.append_rows(rows, end_offset_token=end_offset)

    def flush(self) -> None:
        self._channel.wait_for_commit(lambda token: True, timeout_seconds=120)

    def close(self) -> None:
        self._channel.close()
        self._client.close()


def _read_rows(path: Path) -> Iterator[dict]:
    with gzip.open(path, "rb") as raw, io.TextIOWrapper(raw, encoding="utf-8", newline="") as text:
        yield from csv.DictReader(text)


def stream_file(
    conn_name: str,
    domain: str,
    path: Path,
    batch_size: int = 5000,
    sink_factory: Callable[[str, str], RowSink] = SdkSink,
) -> int:
    """Send every row of `path`; returns rows sent. The sink is always closed."""
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")
    if not path.exists():
        raise FileNotFoundError(path)
    sink = sink_factory(conn_name, domain)
    sent, batch = 0, []
    try:
        for row in _read_rows(path):
            batch.append(row)
            if len(batch) == batch_size:
                sent += len(batch)
                sink.append(batch, str(sent))
                batch = []
        if batch:
            sent += len(batch)
            sink.append(batch, str(sent))
        sink.flush()
    finally:
        sink.close()
    return sent


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="stream-load")
    p.add_argument("--connection", default="handson_tf")
    p.add_argument("--domain", required=True)
    p.add_argument("--file", type=Path, required=True)
    p.add_argument("--batch-size", type=int, default=5000)
    a = p.parse_args(argv)
    n = stream_file(a.connection, a.domain, a.file, a.batch_size)
    print(f"streamed {n} rows into {a.domain}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
