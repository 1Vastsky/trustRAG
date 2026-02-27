"""Shamir secret sharing over a prime field.

Field prime (default): 2^127 - 1.
"""

from __future__ import annotations

from secrets import randbelow
from typing import Iterable, List, Sequence, Tuple

DEFAULT_PRIME = (1 << 127) - 1
Share = Tuple[int, int]


def field_add(a: int, b: int, p: int) -> int:
    return (a + b) % p


def field_sub(a: int, b: int, p: int) -> int:
    return (a - b) % p


def field_mul(a: int, b: int, p: int) -> int:
    return (a * b) % p


def field_inv(a: int, p: int) -> int:
    a %= p
    if a == 0:
        raise ValueError("zero has no multiplicative inverse")
    return pow(a, -1, p)


def field_div(a: int, b: int, p: int) -> int:
    return field_mul(a, field_inv(b, p), p)


def _validate_params(secret: int, t: int, n: int, p: int) -> None:
    if p <= 2:
        raise ValueError("p must be a prime > 2")
    if t < 1:
        raise ValueError("t must be >= 1")
    if n < t:
        raise ValueError("n must be >= t")
    if secret < 0 or secret >= p:
        raise ValueError("secret must satisfy 0 <= secret < p")


def _poly_eval(coeffs: Sequence[int], x: int, p: int) -> int:
    acc = 0
    for coeff in reversed(coeffs):
        acc = field_add(field_mul(acc, x, p), coeff, p)
    return acc


def shamir_split(secret: int, t: int, n: int, p: int = DEFAULT_PRIME) -> List[Share]:
    """Split a secret into n shares with threshold t."""
    _validate_params(secret, t, n, p)
    coeffs = [secret] + [randbelow(p) for _ in range(t - 1)]
    return [(x, _poly_eval(coeffs, x, p)) for x in range(1, n + 1)]


def _normalize_shares(shares: Iterable[Share], p: int) -> List[Share]:
    result: List[Share] = []
    seen_x = set()
    for x, y in shares:
        if x in seen_x:
            raise ValueError("duplicate share x value")
        if x == 0:
            raise ValueError("share x must be non-zero")
        seen_x.add(x)
        result.append((x % p, y % p))
    if not result:
        raise ValueError("at least one share is required")
    return result


def shamir_reconstruct(shares: Sequence[Share], p: int = DEFAULT_PRIME) -> int:
    """Reconstruct secret via Lagrange interpolation evaluated at x=0."""
    points = _normalize_shares(shares, p)
    secret = 0

    for j, (xj, yj) in enumerate(points):
        numerator = 1
        denominator = 1
        for m, (xm, _) in enumerate(points):
            if m == j:
                continue
            numerator = field_mul(numerator, (-xm) % p, p)
            denominator = field_mul(denominator, field_sub(xj, xm, p), p)
        lagrange_at_zero = field_div(numerator, denominator, p)
        secret = field_add(secret, field_mul(yj, lagrange_at_zero, p), p)
    return secret
