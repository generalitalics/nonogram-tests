#!/usr/bin/env python3
"""Simple test runner for full and smoke API suites."""
from __future__ import annotations

import argparse
import subprocess
import sys
from typing import List


def build_pytest_cmd(mode: str, extra_args: List[str]) -> List[str]:
    cmd = ["pytest"]
    if mode == "smoke":
        cmd.extend(["-m", "smoke"])
    cmd.extend(extra_args)
    return cmd


def main() -> int:
    parser = argparse.ArgumentParser(description="Run nonogram API tests")
    parser.add_argument(
        "mode",
        nargs="?",
        choices=("all", "smoke"),
        default="all",
        help="Test subset to run",
    )
    parser.add_argument(
        "--",
        dest="pytest_args",
        nargs=argparse.REMAINDER,
        default=[],
        help="Arguments passed through to pytest",
    )
    args = parser.parse_args()

    passthrough = args.pytest_args
    if passthrough and passthrough[0] == "--":
        passthrough = passthrough[1:]

    cmd = build_pytest_cmd(args.mode, passthrough)
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
