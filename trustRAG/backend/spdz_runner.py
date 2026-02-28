"""MP-SPDZ runner helpers for secure-sum subroutines."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable, List, Tuple

from backend.shamir import DEFAULT_PRIME

MPC_DIR = Path(__file__).resolve().parent.parent / "mpc"
RUN_SCRIPT = MPC_DIR / "run_spdz.sh"


def _normalize(values: Iterable[int], p: int) -> List[int]:
    return [v % p for v in values]


def _parse_sum_output(stdout: str, p: int) -> int:
    for line in reversed(stdout.strip().splitlines()):
        line = line.strip()
        if not line:
            continue
        if line.startswith("SUM="):
            return int(line.split("=", 1)[1]) % p
        try:
            return int(line) % p
        except ValueError:
            continue
    raise ValueError(f"failed to parse sum from output: {stdout!r}")


def run_spdz_sum(values: Iterable[int], p: int = DEFAULT_PRIME) -> int:
    """Run secure sum for a node's local values via MP-SPDZ wrapper script."""
    normalized = _normalize(values, p)
    if not normalized:
        return 0
    if not RUN_SCRIPT.exists():
        raise FileNotFoundError(f"SPDZ runner script not found: {RUN_SCRIPT}")

    values_csv = ",".join(str(v) for v in normalized)
    proc = subprocess.run(
        ["bash", str(RUN_SCRIPT), values_csv, str(p)],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"SPDZ sum failed: {proc.stderr.strip() or proc.stdout.strip()}")
    return _parse_sum_output(proc.stdout, p)


def run_spdz_pair(s_values: Iterable[int], r_values: Iterable[int], p: int = DEFAULT_PRIME) -> Tuple[int, int]:
    """Compute secure sums for s and r lists."""
    s_sum = run_spdz_sum(s_values, p=p)
    r_sum = run_spdz_sum(r_values, p=p)
    return s_sum, r_sum
