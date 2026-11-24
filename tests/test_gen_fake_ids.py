import random

from hanbit_gen.fakers import fake_rrn, is_valid_rrn


def test_validator_accepts_a_known_valid_number():
    # constructed: weights 2,3,4,5,6,7,8,9,2,3,4,5 over 123456123456 -> check digit 0
    digits = "123456123456"
    total = sum(int(d) * w for d, w in zip(digits, [2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5]))
    assert is_valid_rrn(digits + str((11 - total % 11) % 10))


def test_fake_rrn_check_digit_always_invalid():
    rng = random.Random(0)
    samples = [fake_rrn(rng) for _ in range(1000)]
    assert all(len(s) == 13 and s.isdigit() for s in samples)
    assert not any(is_valid_rrn(s) for s in samples)
