"""Deterministic tests for share aggregation + reconstruction."""

from backend.shamir import DEFAULT_PRIME, shamir_reconstruct, shamir_split
from backend.spdz_runner import run_spdz_pair


def test_share_totals_reconstruct_true_sum() -> None:
    scores = [7, 12, 20, 5, 3]
    blinds = [101, 202, 303, 404, 505]
    t = 3
    n = 5
    p = DEFAULT_PRIME

    node_s_values = {x: [] for x in range(1, n + 1)}
    node_r_values = {x: [] for x in range(1, n + 1)}

    for score, blind in zip(scores, blinds):
        s_shares = shamir_split(score, t=t, n=n, p=p)
        r_shares = shamir_split(blind, t=t, n=n, p=p)
        for x, y in s_shares:
            node_s_values[x].append(y)
        for x, y in r_shares:
            node_r_values[x].append(y)

    s_total_shares = []
    r_total_shares = []
    for x in range(1, n + 1):
        s_share, r_share = run_spdz_pair(node_s_values[x], node_r_values[x], p=p)
        s_total_shares.append((x, s_share))
        r_total_shares.append((x, r_share))

    S = shamir_reconstruct(s_total_shares[:t], p=p)
    R = shamir_reconstruct(r_total_shares[:t], p=p)

    assert S == (sum(scores) % p)
    assert R == (sum(blinds) % p)
