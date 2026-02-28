# PROJECT_SPEC

## Goal

Minimal verifiable decentralized RAG aggregation demo:
- Pedersen commitments for per-vote hiding.
- Shamir secret sharing for `(s, r)`.
- Committee-side share aggregation via SPDZ runner interface.
- Threshold BLS in Python for aggregation authorization.
- On-chain consistency check for aggregated `(S, R)` against commitment product.

## Components

- `backend/main.py`: document API from CSV.
- `backend/shamir.py`: Shamir split/reconstruct over `p = 2^127 - 1`.
- `backend/pedersen.py`: `C = g^s * h^r mod p` with `g=5, h=7`.
- `backend/committee.py`: share collection and trigger endpoint per node.
- `backend/spdz_runner.py`: wrapper calling `mpc/run_spdz.sh` to sum node-local share lists.
- `backend/bls_threshold.py`: threshold BLS keygen/sign/aggregate/verify using `py_ecc`.
- `contracts/DataChain.sol`: stores vote product + counts, accepts aggregate submission, checks Pedersen equation.

## On-chain BLS Limitation (explicit)

This demo performs BLS verification **off-chain** in Python.
On-chain, `DataChain.submitAggregate(...)` verifies an ECDSA committee attestation over `(docId, rid, S, R, voteCount, sigmaHash)` instead of doing native BLS pairing verification in Solidity.

Reason: keep Solidity minimal and runnable locally without custom BLS12-381 precompile/pairing integration.
