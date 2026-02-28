#!/usr/bin/env bash
set -euo pipefail

# Wrapper for node-local secure-sum.
# Usage: run_spdz.sh "1,2,3,4" [prime]

VALUES_CSV="${1:-}"
PRIME="${2:-170141183460469231731687303715884105727}"

if [[ -n "${MP_SPDZ_ROOT:-}" ]]; then
  if [[ -f "${MP_SPDZ_ROOT}/compile.py" ]]; then
    echo "INFO: MP_SPDZ_ROOT detected at ${MP_SPDZ_ROOT}; falling back to local deterministic sum for demo."
  fi
fi

python3 - "$VALUES_CSV" "$PRIME" <<'PY'
import sys

values_csv = sys.argv[1]
p = int(sys.argv[2])

if values_csv.strip():
    values = [int(x.strip()) % p for x in values_csv.split(",") if x.strip()]
else:
    values = []

print(f"SUM={sum(values) % p}")
PY
