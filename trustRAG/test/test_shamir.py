"""Unit tests for Shamir split/reconstruct."""

from backend.shamir import DEFAULT_PRIME, shamir_reconstruct, shamir_split


def test_split_reconstruct_with_threshold_subset() -> None:
    secret = 12345678901234567890
    shares = shamir_split(secret=secret, t=3, n=5, p=DEFAULT_PRIME)
    recovered = shamir_reconstruct(shares[:3], p=DEFAULT_PRIME)
    assert recovered == secret


def test_split_reconstruct_with_all_shares() -> None:
    secret = DEFAULT_PRIME - 2
    shares = shamir_split(secret=secret, t=4, n=7, p=DEFAULT_PRIME)
    recovered = shamir_reconstruct(shares, p=DEFAULT_PRIME)
    assert recovered == secret


def test_split_reconstruct_with_nonconsecutive_subset() -> None:
    secret = 42
    shares = shamir_split(secret=secret, t=3, n=6, p=DEFAULT_PRIME)
    subset = [shares[0], shares[3], shares[5]]
    recovered = shamir_reconstruct(subset, p=DEFAULT_PRIME)
    assert recovered == secret


def test_reconstruct_rejects_duplicate_x() -> None:
    shares = [(1, 10), (1, 22), (2, 19)]
    try:
        shamir_reconstruct(shares, p=DEFAULT_PRIME)
        assert False, "expected ValueError for duplicate x"
    except ValueError as exc:
        assert "duplicate" in str(exc)
