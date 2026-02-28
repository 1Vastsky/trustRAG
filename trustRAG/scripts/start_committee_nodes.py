"""Launch N committee nodes on ports 9001..900N."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from typing import List


def launch_nodes(n: int, host: str = "127.0.0.1", base_port: int = 9000) -> List[subprocess.Popen]:
    processes: List[subprocess.Popen] = []
    for idx in range(1, n + 1):
        port = base_port + idx
        env = os.environ.copy()
        env["COMMITTEE_NODE_ID"] = str(idx)
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.committee:app",
            "--host",
            host,
            "--port",
            str(port),
        ]
        proc = subprocess.Popen(cmd, env=env)
        processes.append(proc)
        print(f"started node={idx} port={port} pid={proc.pid}")
    return processes


def stop_nodes(processes: List[subprocess.Popen]) -> None:
    for proc in processes:
        if proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
    for proc in processes:
        if proc.poll() is None:
            proc.wait(timeout=10)


def main() -> int:
    parser = argparse.ArgumentParser(description="Start committee node services.")
    parser.add_argument("--n", type=int, default=3, help="number of committee nodes")
    parser.add_argument("--host", default="127.0.0.1", help="host bind address")
    parser.add_argument("--base-port", type=int, default=9000, help="base port; nodes start at base+1")
    args = parser.parse_args()

    if args.n < 1:
        print("n must be >= 1", file=sys.stderr)
        return 1

    processes = launch_nodes(n=args.n, host=args.host, base_port=args.base_port)
    print("all committee nodes started; press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
            for proc in processes:
                if proc.poll() is not None:
                    print(f"node process exited unexpectedly pid={proc.pid} code={proc.returncode}")
                    return 1
    except KeyboardInterrupt:
        print("\nstopping committee nodes...")
        stop_nodes(processes)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
