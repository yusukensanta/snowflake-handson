import gzip
import json

import pytest

from hanbit_gen.cli import main
from hanbit_gen.generator import generate
from hanbit_gen.schema import DOMAINS, REGIONS, SCHEMAS


def read_lines(path):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return fh.read().splitlines()


def test_every_domain_has_schema_and_file(tmp_path):
    assert set(SCHEMAS) == set(DOMAINS)
    for d in DOMAINS:
        out = generate(d, seed=1, rows=5, out_dir=tmp_path)
        assert out.name == f"{d}.csv.gz"
        assert len(read_lines(out)) == 6  # header + 5 rows


def test_claims_contains_health_columns():
    sens = {c.name: c.sensitivity for c in SCHEMAS["claims"]}
    assert sens["diagnosis_code"] == "health"
    assert sens["claim_note"] == "health"


def test_region_values_limited_to_known_set(tmp_path):
    out = generate("claims", seed=3, rows=200, out_dir=tmp_path)
    header, *rows = read_lines(out)
    idx = header.split(",").index("region")
    assert {r.split(",")[idx] for r in rows} <= set(REGIONS)


def test_rows_param_respected(tmp_path):
    assert len(read_lines(generate("lending", seed=1, rows=17, out_dir=tmp_path))) == 18


def test_ndjson_format_has_one_json_object_per_row(tmp_path):
    out = generate("finance", seed=1, rows=3, out_dir=tmp_path, fmt="ndjson")
    assert out.name == "finance.ndjson.gz"
    assert all(set(json.loads(line)) == {c.name for c in SCHEMAS["finance"]} for line in read_lines(out))


def test_unknown_domain_raises(tmp_path):
    with pytest.raises(ValueError, match="unknown domain"):
        generate("nope", seed=1, rows=1, out_dir=tmp_path)


def test_cli_rejects_unknown_domain(tmp_path, capsys):
    assert main(["--domain", "nope", "--out", str(tmp_path)]) == 64
    assert "unknown domain" in capsys.readouterr().err


def test_cli_emit_tag_map_lists_only_sensitive_columns(tmp_path):
    target = tmp_path / "tags.json"
    assert main(["--emit-tag-map", str(target)]) == 0
    tags = json.loads(target.read_text())["column_sensitivity"]
    assert tags["claims.diagnosis_code"] == "health"
    assert tags["lending.credit_score"] == "credit"
    assert "claims.claim_id" not in tags


def test_cli_generates_all_domains_with_rows(tmp_path):
    assert main(["--rows", "4", "--out", str(tmp_path)]) == 0
    assert len(list(tmp_path.glob("*.csv.gz"))) == len(DOMAINS)
