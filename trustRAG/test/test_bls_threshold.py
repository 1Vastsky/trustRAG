"""Tests for threshold BLS signing."""

from backend.bls_threshold import aggregate_sig, keygen_threshold, partial_sign, verify


def test_threshold_bls_sign_and_verify() -> None:
    pubkey, shares = keygen_threshold(t=3, n=5)
    msg = b"rid=1|doc=doc1|S=100|R=999|votes=20"

    selected = [shares[0], shares[2], shares[4]]
    xs = [x for x, _ in selected]
    sig_shares = [partial_sign(sk_share, msg) for sk_share in selected]
    sigma = aggregate_sig(sig_shares, xs)

    assert verify(pubkey, msg, sigma) is True
    assert verify(pubkey, b"wrong-message", sigma) is False
