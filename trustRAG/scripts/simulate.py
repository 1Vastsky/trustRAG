"""End-to-end local simulation for TrustRAG demo."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import random
import signal
import subprocess
import sys
import time
import warnings
from pathlib import Path
from typing import List, Sequence, Tuple

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL 1.1.1+.*")

import httpx
from eth_abi import encode
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_tester import EthereumTester, PyEVMBackend
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

from backend.bls_threshold import aggregate_sig, keygen_threshold, partial_sign, verify
from backend.pedersen import P, commit, product_commitments
from backend.shamir import shamir_reconstruct, shamir_split

ROOT_DIR = Path(__file__).resolve().parents[1]
ARTIFACT_PATH = ROOT_DIR / "artifacts" / "contracts" / "DataChain.sol" / "DataChain.json"
DOCS_CSV = ROOT_DIR / "backend" / "docs.csv"
BASE_PORT = 9000
HOST = "127.0.0.1"


def ensure_compiled() -> None:
    subprocess.run(["npx", "hardhat", "compile"], cwd=ROOT_DIR, check=True, capture_output=True, text=True)


def load_artifact() -> Tuple[List[dict], str]:
    with ARTIFACT_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data["abi"], data["bytecode"]


def launch_committee_nodes(n: int) -> List[subprocess.Popen]:
    processes: List[subprocess.Popen] = []
    for node_id in range(1, n + 1):
        port = BASE_PORT + node_id
        env = os.environ.copy()
        env["COMMITTEE_NODE_ID"] = str(node_id)
        env["PYTHONPATH"] = str(ROOT_DIR)
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.committee:app",
            "--host",
            HOST,
            "--port",
            str(port),
        ]
        processes.append(subprocess.Popen(cmd, cwd=ROOT_DIR, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    return processes


def stop_processes(processes: Sequence[subprocess.Popen]) -> None:
    for p in processes:
        if p.poll() is None:
            p.send_signal(signal.SIGTERM)
    deadline = time.time() + 8
    for p in processes:
        if p.poll() is not None:
            continue
        timeout = max(0.0, deadline - time.time())
        if timeout <= 0:
            break
        try:
            p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            pass
    for p in processes:
        if p.poll() is None:
            p.kill()


def wait_for_committees(n: int, timeout_sec: float = 20.0) -> None:
    deadline = time.time() + timeout_sec
    with httpx.Client(timeout=1.0) as client:
        for node_id in range(1, n + 1):
            url = f"http://{HOST}:{BASE_PORT + node_id}/health"
            while True:
                try:
                    resp = client.get(url)
                    if resp.status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                if time.time() > deadline:
                    raise TimeoutError(f"committee node {node_id} did not start in time")
                time.sleep(0.2)


def deploy_contract(abi: List[dict], bytecode: str, committee_accounts: List[str], threshold: int):
    backend = PyEVMBackend()
    eth_tester = EthereumTester(backend=backend)
    w3 = Web3(EthereumTesterProvider(eth_tester))
    acct0 = w3.eth.accounts[0]
    contract_factory = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx_hash = contract_factory.constructor(committee_accounts, threshold).transact({"from": acct0})
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    contract = w3.eth.contract(address=receipt.contractAddress, abi=abi)
    return w3, backend, contract


def build_bls_message(rid: int, doc_id: str, S: int, R: int, vote_count: int) -> bytes:
    payload = f"rid={rid}|doc={doc_id}|S={S}|R={R}|votes={vote_count}".encode("utf-8")
    return hashlib.sha256(payload).digest()


def build_attestation_digest(
    contract_address: str,
    chain_id: int,
    doc_id: str,
    rid: int,
    S: int,
    R: int,
    vote_count: int,
    sigma: bytes,
) -> bytes:
    sigma_hash = Web3.keccak(sigma)
    encoded = encode(
        ["address", "uint256", "string", "uint256", "uint256", "uint256", "uint256", "bytes32"],
        [contract_address, chain_id, doc_id, rid, S, R, vote_count, sigma_hash],
    )
    return Web3.keccak(encoded)


def sign_digest_with_key(digest: bytes, private_key_hex: str) -> bytes:
    msg = encode_defunct(hexstr=digest.hex())
    signed = Account.sign_message(msg, private_key=private_key_hex)
    return signed.signature


def read_doc_text(doc_id: str) -> str:
    with DOCS_CSV.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("doc_id") == doc_id:
                return row.get("text", "")
    return ""


def main() -> int:
    rid = 1
    doc_id = "doc1"
    num_votes = 20
    committee_n = 4
    threshold_t = 3

    ensure_compiled()
    abi, bytecode = load_artifact()

    processes = launch_committee_nodes(committee_n)
    try:
        wait_for_committees(committee_n)

        # Deploy chain and derive committee signer keys from local eth_tester backend.
        backend = PyEVMBackend()
        eth_tester = EthereumTester(backend=backend)
        w3 = Web3(EthereumTesterProvider(eth_tester))
        committee_accounts = list(w3.eth.accounts[:committee_n])
        committee_privkeys = [backend.account_keys[i].to_hex() for i in range(committee_n)]

        contract_factory = w3.eth.contract(abi=abi, bytecode=bytecode)
        deploy_tx = contract_factory.constructor(committee_accounts, threshold_t).transact({"from": w3.eth.accounts[0]})
        deploy_receipt = w3.eth.wait_for_transaction_receipt(deploy_tx)
        contract = w3.eth.contract(address=deploy_receipt.contractAddress, abi=abi)

        # Threshold BLS material.
        bls_pubkey, bls_sk_shares = keygen_threshold(t=threshold_t, n=committee_n)
        share_by_x = {x: (x, sk) for x, sk in bls_sk_shares}

        rng = random.Random(20260228)
        expected_S = 0
        expected_R = 0
        commitments: List[int] = []

        with httpx.Client(timeout=5.0) as client:
            for i in range(1, num_votes + 1):
                voter_id = f"v{i}"
                s_i = i % 51
                # Keep blinded values small in this demo so reconstructed R equals exponent sum directly.
                r_i = rng.randrange(1, 10_000_000)
                expected_S = (expected_S + s_i) % P
                expected_R = (expected_R + r_i) % P

                C_i = commit(s_i, r_i)
                commitments.append(C_i)

                tx = contract.functions.submitVote(doc_id, rid, C_i).transact({"from": w3.eth.accounts[0]})
                w3.eth.wait_for_transaction_receipt(tx)

                s_shares = shamir_split(s_i, t=threshold_t, n=committee_n, p=P)
                r_shares = shamir_split(r_i, t=threshold_t, n=committee_n, p=P)

                for k in range(committee_n):
                    url = f"http://{HOST}:{BASE_PORT + k + 1}/share"
                    payload = {
                        "rid": rid,
                        "doc_id": doc_id,
                        "voter_id": voter_id,
                        "s_share": {"x": s_shares[k][0], "y": s_shares[k][1]},
                        "r_share": {"x": r_shares[k][0], "y": r_shares[k][1]},
                    }
                    resp = client.post(url, json=payload)
                    resp.raise_for_status()

            s_total_shares = []
            r_total_shares = []
            selected_xs: List[int] = []
            for node_id in range(1, threshold_t + 1):
                url = f"http://{HOST}:{BASE_PORT + node_id}/trigger/{rid}/{doc_id}"
                resp = client.post(url)
                resp.raise_for_status()
                body = resp.json()
                if body.get("status") != "ok":
                    raise RuntimeError(f"node {node_id} trigger failed: {body}")
                share = body["share"]
                selected_xs.append(share["x"])
                s_total_shares.append((share["x"], share["s_y"]))
                r_total_shares.append((share["x"], share["r_y"]))

        S = shamir_reconstruct(s_total_shares, p=P)
        R = shamir_reconstruct(r_total_shares, p=P)
        vote_count = contract.functions.voteCount(doc_id, rid).call()

        msg = build_bls_message(rid, doc_id, S, R, vote_count)
        sig_shares = [partial_sign(share_by_x[x], msg) for x in selected_xs]
        sigma = aggregate_sig(sig_shares, selected_xs)
        if not verify(bls_pubkey, msg, sigma):
            raise RuntimeError("BLS aggregated signature verification failed")

        digest = build_attestation_digest(contract.address, w3.eth.chain_id, doc_id, rid, S, R, vote_count, sigma)
        attestations = [sign_digest_with_key(digest, committee_privkeys[i]) for i in range(threshold_t)]

        submit_tx = contract.functions.submitAggregate(doc_id, rid, S, R, vote_count, sigma, attestations).transact(
            {"from": w3.eth.accounts[0]}
        )
        submit_receipt = w3.eth.wait_for_transaction_receipt(submit_tx)
        if submit_receipt.status != 1:
            raise RuntimeError("submitAggregate transaction reverted")

        onchain_product = contract.functions.getProduct(doc_id, rid).call()
        onchain_S = contract.functions.aggregatedS(doc_id, rid).call()
        onchain_R = contract.functions.aggregatedR(doc_id, rid).call()
        onchain_votes = contract.functions.aggregatedVoteCount(doc_id, rid).call()
        expected_product = product_commitments(commitments)
        doc_text = read_doc_text(doc_id)
        weight = onchain_S / onchain_votes

        print("=== Simulation Result ===")
        print(f"Expected S={expected_S}, Expected R={expected_R}")
        print(f"SPDZ output S={S}, R={R}")
        print(f"On-chain productCommitment={onchain_product}")
        print(f"Expected productCommitment={expected_product}")
        print(f"Contract verification success={submit_receipt.status == 1}")
        print(f"On-chain aggregated S={onchain_S}, R={onchain_R}, vote_count={onchain_votes}")
        print(f"Weight (S/vote_count)={weight}")
        print(f"Doc {doc_id}: {doc_text}")

        if expected_S != S or expected_R != R:
            raise RuntimeError("reconstructed sums do not match expected sums")
        if expected_product != onchain_product:
            raise RuntimeError("on-chain product does not match expected product")
        if onchain_S != S or onchain_R != R or onchain_votes != vote_count:
            raise RuntimeError("on-chain aggregate state mismatch")
        return 0
    finally:
        stop_processes(processes)


if __name__ == "__main__":
    raise SystemExit(main())
