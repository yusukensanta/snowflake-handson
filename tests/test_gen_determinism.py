import hashlib

from hanbit_gen.generator import generate


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_same_seed_same_bytes(tmp_path):
    a = generate("claims", seed=42, rows=50, out_dir=tmp_path / "a")
    b = generate("claims", seed=42, rows=50, out_dir=tmp_path / "b")
    assert digest(a) == digest(b)


def test_different_seed_different_bytes(tmp_path):
    a = generate("claims", seed=1, rows=50, out_dir=tmp_path / "a")
    b = generate("claims", seed=2, rows=50, out_dir=tmp_path / "b")
    assert digest(a) != digest(b)
