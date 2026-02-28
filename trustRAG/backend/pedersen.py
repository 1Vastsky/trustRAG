"""Pedersen commitments in multiplicative group modulo a prime P."""

from __future__ import annotations

from typing import Iterable

# Demo parameters shared with Solidity contract.
P = (1 << 127) - 1
G = 5
H = 7


def normalize_scalar(x: int, p: int = P) -> int:
    return x % p


def commit(s: int, r: int, p: int = P, g: int = G, h: int = H) -> int:
    s_n = normalize_scalar(s, p)
    r_n = normalize_scalar(r, p)
    return (pow(g, s_n, p) * pow(h, r_n, p)) % p


def verify_open(C: int, s: int, r: int, p: int = P, g: int = G, h: int = H) -> bool:
    return (C % p) == commit(s=s, r=r, p=p, g=g, h=h)


def product_commitments(commitments: Iterable[int], p: int = P) -> int:
    acc = 1
    for c in commitments:
        acc = (acc * (c % p)) % p
    return acc
