"""The warehouse list lives in two places (shell scripts and Terraform); keep them identical."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _script_warehouses() -> list[str]:
    text = (ROOT / "scripts/lib/common.sh").read_text()
    m = re.search(r'^WAREHOUSE_MONITORS="([^"]+)"', text, re.MULTILINE)
    assert m, "WAREHOUSE_MONITORS not found in scripts/lib/common.sh"
    return [pair.split(":")[0] for pair in m.group(1).split()]


def _terraform_warehouses() -> list[str]:
    text = (ROOT / "terraform/envs/handson/main.tf").read_text()
    m = re.search(r"for w in \[([^\]]+)\]", text)
    assert m, "warehouse_monitors local not found in terraform/envs/handson/main.tf"
    return re.findall(r'"([A-Z_]+)"', m.group(1))


def test_script_and_terraform_warehouses_match():
    assert _script_warehouses() == _terraform_warehouses()


def test_quotas_are_whole_numbers():
    text = (ROOT / "scripts/lib/common.sh").read_text()
    pairs = re.search(r'^WAREHOUSE_MONITORS="([^"]+)"', text, re.MULTILINE).group(1).split()
    assert all(p.split(":")[1].isdigit() for p in pairs)
