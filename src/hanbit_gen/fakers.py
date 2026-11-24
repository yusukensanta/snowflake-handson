"""Seeded fake-value helpers. Only `random.Random` instances are used (no global state, no clock)."""
from __future__ import annotations

import random
from datetime import date, timedelta

_WEIGHTS = [2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5]
_SURNAMES = ["Kim", "Lee", "Park", "Choi", "Jung", "Kang", "Cho", "Yoon", "Jang", "Lim"]
_GIVEN = ["Minjun", "Seoyeon", "Jiho", "Haeun", "Dohyun", "Yuna", "Joon", "Sua", "Taeyang", "Nari"]
_STREETS = ["Teheran-ro", "Sejong-daero", "Gangnam-daero", "Hwarang-ro", "Jungang-ro"]
_DIAGNOSES = ["J06.9", "K29.7", "M54.5", "S82.0", "I10", "E11.9", "F32.1", "C50.9"]
_NOTES = ["outpatient visit", "surgery follow-up", "physiotherapy course", "emergency admission"]


def is_valid_rrn(value: str) -> bool:
    if len(value) != 13 or not value.isdigit():
        return False
    total = sum(int(d) * w for d, w in zip(value[:12], _WEIGHTS))
    return int(value[12]) == (11 - total % 11) % 10


def fake_rrn(rng: random.Random) -> str:
    """13 digits shaped like a Korean RRN whose check digit is deliberately WRONG."""
    body = "".join(str(rng.randrange(10)) for _ in range(12))
    total = sum(int(d) * w for d, w in zip(body, _WEIGHTS))
    valid = (11 - total % 11) % 10
    return body + str((valid + 1 + rng.randrange(9)) % 10)


def fake_name(rng: random.Random) -> str:
    return f"{rng.choice(_SURNAMES)} {rng.choice(_GIVEN)}"


def fake_phone(rng: random.Random) -> str:
    return f"010-{rng.randrange(1000, 10000)}-{rng.randrange(1000, 10000)}"


def fake_address(rng: random.Random, region: str) -> str:
    return f"{rng.randrange(1, 300)} {rng.choice(_STREETS)}, {region}"


def fake_diagnosis(rng: random.Random) -> str:
    return rng.choice(_DIAGNOSES)


def fake_note(rng: random.Random) -> str:
    return rng.choice(_NOTES)


def fake_date(rng: random.Random, start: date = date(2023, 1, 1), days: int = 1100) -> str:
    return (start + timedelta(days=rng.randrange(days))).isoformat()
