"""Threshold BLS utilities using py_ecc (BLS12-381)."""

from __future__ import annotations

from secrets import randbelow
from typing import Iterable, List, Sequence, Tuple

from py_ecc.bls import G2ProofOfPossession as bls_pop
from py_ecc.bls.g2_primitives import G2_to_signature, signature_to_G2
from py_ecc.optimized_bls12_381 import Z2, add, curve_order, multiply

SkShare = Tuple[int, int]


def _inv_mod(x: int, q: int) -> int:
    x %= q
    if x == 0:
        raise ValueError("division by zero in finite field")
    return pow(x, -1, q)


def _poly_eval(coeffs: Sequence[int], x: int, q: int) -> int:
    acc = 0
    for c in reversed(coeffs):
        acc = (acc * x + c) % q
    return acc


def _lagrange_at_zero(xj: int, xs: Iterable[int], q: int) -> int:
    num = 1
    den = 1
    for xm in xs:
        if xm == xj:
            continue
        num = (num * (-xm % q)) % q
        den = (den * ((xj - xm) % q)) % q
    return (num * _inv_mod(den, q)) % q


def keygen_threshold(t: int, n: int) -> Tuple[bytes, List[SkShare]]:
    """Create threshold BLS key material (pubkey, secret key shares)."""
    if t < 1:
        raise ValueError("t must be >= 1")
    if n < t:
        raise ValueError("n must be >= t")

    q = curve_order
    master_sk = randbelow(q - 1) + 1
    coeffs = [master_sk] + [randbelow(q) for _ in range(t - 1)]
    sk_shares = [(x, _poly_eval(coeffs, x, q)) for x in range(1, n + 1)]
    pubkey = bls_pop.SkToPk(master_sk)
    return pubkey, sk_shares


def partial_sign(sk_share: SkShare, msg: bytes) -> bytes:
    """Sign a message with one threshold secret-key share."""
    _, sk = sk_share
    return bls_pop.Sign(sk, msg)


def aggregate_sig(sig_shares: Sequence[bytes], xs: Sequence[int]) -> bytes:
    """Aggregate t partial signatures into a full threshold signature."""
    if len(sig_shares) != len(xs):
        raise ValueError("sig_shares and xs length mismatch")
    if not sig_shares:
        raise ValueError("at least one signature share is required")

    q = curve_order
    distinct_xs = list(xs)
    if len(set(distinct_xs)) != len(distinct_xs):
        raise ValueError("xs must be unique")

    agg = Z2
    for sig_share, xj in zip(sig_shares, distinct_xs):
        lam = _lagrange_at_zero(xj, distinct_xs, q)
        point = signature_to_G2(sig_share)
        agg = add(agg, multiply(point, lam))
    return G2_to_signature(agg)


def verify(pubkey: bytes, msg: bytes, sigma: bytes) -> bool:
    """Verify final aggregated signature against the master public key."""
    return bls_pop.Verify(pubkey, msg, sigma)
