"""Deterministic row generation and gzip writers."""
from __future__ import annotations

import csv
import gzip
import io
import json
import random
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from . import fakers as f
from .schema import REGIONS, SCHEMAS

Row = dict[str, object]


def _customer(rng: random.Random, pool: int) -> str:
    return f"C{rng.randrange(pool):07d}"


def _region(rng: random.Random) -> str:
    return rng.choice(REGIONS)


def _make_rows(domain: str) -> Callable[[random.Random, int, int], Row]:
    def underwriting(rng, i, pool):
        region = _region(rng)
        return {"policy_id": f"P{i:08d}", "customer_id": _customer(rng, pool),
                "customer_name": f.fake_name(rng), "rrn": f.fake_rrn(rng), "phone": f.fake_phone(rng),
                "address": f.fake_address(rng, region), "region": region,
                "product": rng.choice(["auto", "health", "life", "property"]),
                "annual_premium": rng.randrange(200, 5000) * 1000, "start_date": f.fake_date(rng)}

    def claims(rng, i, pool):
        return {"claim_id": f"CL{i:08d}", "policy_id": f"P{rng.randrange(max(i, 1)):08d}",
                "customer_id": _customer(rng, pool), "region": _region(rng),
                "diagnosis_code": f.fake_diagnosis(rng), "claim_note": f.fake_note(rng),
                "claim_amount": rng.randrange(50, 20000) * 1000,
                "status": rng.choice(["filed", "review", "paid", "denied"]), "filed_date": f.fake_date(rng)}

    def lending(rng, i, pool):
        region = _region(rng)
        return {"loan_id": f"L{i:08d}", "customer_id": _customer(rng, pool),
                "customer_name": f.fake_name(rng), "rrn": f.fake_rrn(rng),
                "branch": f"{region}-{rng.randrange(1, 4)}", "region": region,
                "credit_score": rng.randrange(300, 1000), "annual_income": rng.randrange(20, 200) * 1_000_000,
                "loan_amount": rng.randrange(5, 500) * 1_000_000,
                "status": rng.choice(["applied", "approved", "active", "closed", "default"])}

    def finance(rng, i, pool):
        return {"entry_id": f"E{i:09d}", "account_code": rng.choice(["1100", "2100", "4100", "5100"]),
                "region": _region(rng), "amount": rng.randrange(-5000, 5000) * 1000,
                "posted_date": f.fake_date(rng)}

    def risk_fraud(rng, i, pool):
        return {"flag_id": f"F{i:08d}", "claim_id": f"CL{rng.randrange(max(i, 1)):08d}",
                "customer_id": _customer(rng, pool), "score": round(rng.random() * 100, 2),
                "flag_reason": rng.choice(["duplicate claim", "timing", "network link", "amount outlier"])}

    def marketing(rng, i, pool):
        return {"segment_id": f"S{i:08d}", "customer_id": _customer(rng, pool), "region": _region(rng),
                "age_band": rng.choice(["20s", "30s", "40s", "50s", "60+"]),
                "campaign": rng.choice(["spring", "summer", "autumn", "winter"]),
                "converted": rng.random() < 0.12}

    return {"underwriting": underwriting, "claims": claims, "lending": lending, "finance": finance,
            "risk_fraud": risk_fraud, "marketing": marketing}[domain]


def generate(domain: str, seed: int, rows: int, out_dir: Path,
             fmt: Literal["csv", "ndjson"] = "csv") -> Path:
    """Write `<domain>.<fmt>.gz` into out_dir; identical output for identical arguments."""
    if domain not in SCHEMAS:
        raise ValueError(f"unknown domain: {domain}")
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(f"{seed}:{domain}")
    make = _make_rows(domain)
    cols = [c.name for c in SCHEMAS[domain]]
    pool = max(rows // 3, 1)
    path = out_dir / f"{domain}.{fmt}.gz"
    # mtime=0 and empty filename keep the gzip header (and so the bytes) reproducible
    with (
        open(path, "wb") as raw,
        gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as gz,
        io.TextIOWrapper(gz, encoding="utf-8", newline="") as text,
    ):
        writer = csv.DictWriter(text, fieldnames=cols, lineterminator="\n") if fmt == "csv" else None
        if writer:
            writer.writeheader()
        for i in range(rows):
            row = make(rng, i, pool)
            if writer:
                writer.writerow(row)
            else:
                text.write(json.dumps(row, separators=(",", ":")) + "\n")
    return path
