#!/usr/bin/env python3
"""Simple load test for nonogram backend concurrency limits.

The script stresses the hottest gameplay endpoints:
- POST /progress/save
- POST /progress/load

It creates one temporary level before the run and deletes it after.
All workers share the same username (default: player1 from test DB).
"""

from __future__ import annotations

import argparse
import statistics
import threading
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import httpx


MATRIX_7 = [
    [1, 0, 0, 1, 0, 0, 1],
    [0, 1, 0, 0, 1, 0, 0],
    [0, 0, 1, 0, 0, 1, 0],
    [1, 0, 0, 1, 0, 0, 1],
    [0, 1, 1, 1, 1, 1, 0],
    [0, 0, 1, 0, 0, 1, 0],
    [1, 1, 0, 0, 0, 0, 1],
]


@dataclass
class RequestResult:
    endpoint: str
    status_code: int
    latency_ms: float
    error: Optional[str] = None


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._results: List[RequestResult] = []

    def add(self, item: RequestResult) -> None:
        with self._lock:
            self._results.append(item)

    def snapshot(self) -> List[RequestResult]:
        with self._lock:
            return list(self._results)


def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    values_sorted = sorted(values)
    k = (len(values_sorted) - 1) * p
    f = int(k)
    c = min(f + 1, len(values_sorted) - 1)
    if f == c:
        return values_sorted[f]
    return values_sorted[f] * (c - k) + values_sorted[c] * (k - f)


def create_test_level(client: httpx.Client, difficulty: str) -> Tuple[str, int]:
    label = f"load-test-{uuid.uuid4().hex[:10]}"
    payload = {
        "difficulty": difficulty,
        "matrix": MATRIX_7,
        "label": label,
        "emoji": "L",
    }
    resp = client.post("/api/game/send", json=payload)
    resp.raise_for_status()
    data = resp.json()
    return data["difficulty"], int(data["levelNumber"])


def delete_test_level(client: httpx.Client, difficulty: str, level: int) -> None:
    resp = client.delete(f"/levels/{difficulty}/{level}")
    if resp.status_code not in (200, 404):
        resp.raise_for_status()


def worker_loop(
    worker_id: int,
    base_url: str,
    username: str,
    difficulty: str,
    level: int,
    run_seconds: int,
    save_pause_s: float,
    load_every_n: int,
    metrics: Metrics,
) -> None:
    save_payload = {
        "username": username,
        "difficulty": difficulty,
        "level": level,
        "matrix": MATRIX_7,
        "reason": "auto_save",
    }
    load_payload = {
        "username": username,
        "difficulty": difficulty,
        "level": level,
    }

    deadline = time.perf_counter() + run_seconds
    save_count = 0
    with httpx.Client(base_url=base_url, timeout=10.0) as client:
        while time.perf_counter() < deadline:
            save_count += 1

            t0 = time.perf_counter()
            try:
                resp = client.post("/progress/save", json=save_payload)
                metrics.add(
                    RequestResult(
                        endpoint="save",
                        status_code=resp.status_code,
                        latency_ms=(time.perf_counter() - t0) * 1000,
                        error=None if resp.status_code < 500 else resp.text[:200],
                    )
                )
            except Exception as exc:
                metrics.add(
                    RequestResult(
                        endpoint="save",
                        status_code=0,
                        latency_ms=(time.perf_counter() - t0) * 1000,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )

            if load_every_n > 0 and save_count % load_every_n == 0:
                t1 = time.perf_counter()
                try:
                    resp = client.post("/progress/load", json=load_payload)
                    metrics.add(
                        RequestResult(
                            endpoint="load",
                            status_code=resp.status_code,
                            latency_ms=(time.perf_counter() - t1) * 1000,
                            error=None if resp.status_code < 500 else resp.text[:200],
                        )
                    )
                except Exception as exc:
                    metrics.add(
                        RequestResult(
                            endpoint="load",
                            status_code=0,
                            latency_ms=(time.perf_counter() - t1) * 1000,
                            error=f"{type(exc).__name__}: {exc}",
                        )
                    )

            if save_pause_s > 0:
                time.sleep(save_pause_s)


def summarize(results: List[RequestResult], elapsed_s: float) -> Dict[str, object]:
    if not results:
        return {"total_requests": 0}

    latencies = [r.latency_ms for r in results]
    status_counts = Counter(r.status_code for r in results)
    endpoint_counts = Counter(r.endpoint for r in results)
    error_samples = [r.error for r in results if r.error][:5]

    return {
        "total_requests": len(results),
        "rps": len(results) / elapsed_s if elapsed_s > 0 else 0.0,
        "save_requests": endpoint_counts.get("save", 0),
        "load_requests": endpoint_counts.get("load", 0),
        "status_counts": dict(sorted(status_counts.items())),
        "latency_ms": {
            "mean": round(statistics.mean(latencies), 2),
            "p50": round(percentile(latencies, 0.50), 2),
            "p95": round(percentile(latencies, 0.95), 2),
            "p99": round(percentile(latencies, 0.99), 2),
            "max": round(max(latencies), 2),
        },
        "error_samples": error_samples,
    }


def run_step(
    base_url: str,
    username: str,
    workers: int,
    difficulty: str,
    run_seconds: int,
    save_pause_s: float,
    load_every_n: int,
) -> Dict[str, object]:
    admin_client = httpx.Client(base_url=base_url, timeout=10.0)
    created_difficulty, created_level = create_test_level(admin_client, difficulty)
    metrics = Metrics()
    started = time.perf_counter()
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for worker_id in range(workers):
                pool.submit(
                    worker_loop,
                    worker_id,
                    base_url,
                    username,
                    created_difficulty,
                    created_level,
                    run_seconds,
                    save_pause_s,
                    load_every_n,
                    metrics,
                )
        elapsed = time.perf_counter() - started
        report = summarize(metrics.snapshot(), elapsed)
        report["workers"] = workers
        report["username"] = username
        report["difficulty"] = created_difficulty
        report["level"] = created_level
        report["elapsed_s"] = round(elapsed, 2)
        return report
    finally:
        delete_test_level(admin_client, created_difficulty, created_level)
        admin_client.close()


def print_report(report: Dict[str, object]) -> None:
    print(
        f"\n=== Workers: {report['workers']} | user: {report['username']} | "
        f"duration: {report['elapsed_s']}s ==="
    )
    if report.get("total_requests", 0) == 0:
        print("No requests recorded.")
        return
    print(f"Total requests: {report['total_requests']}, RPS: {report['rps']:.2f}")
    print(f"Save: {report['save_requests']}, Load: {report['load_requests']}")
    print(f"Status counts: {report['status_counts']}")
    lat = report["latency_ms"]
    print(
        "Latency ms:"
        f" mean={lat['mean']}, p50={lat['p50']}, p95={lat['p95']},"
        f" p99={lat['p99']}, max={lat['max']}"
    )
    if report.get("error_samples"):
        print("Error samples:")
        for item in report["error_samples"]:
            print(f"- {item}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load test for nonogram backend")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument(
        "--username",
        default="player1",
        help="All concurrent workers use this user (must exist in DB)",
    )
    parser.add_argument("--difficulty", default="easy", choices=["easy", "medium", "hard"])
    parser.add_argument(
        "--workers-steps",
        default="5,10,20,40,60",
        help="Comma-separated concurrent workers per step, e.g. 5,10,20",
    )
    parser.add_argument("--duration", type=int, default=30, help="Duration per step in seconds")
    parser.add_argument(
        "--save-pause",
        type=float,
        default=0.35,
        help="Pause between save calls per worker; >0.3 avoids debounce cache bias",
    )
    parser.add_argument(
        "--load-every",
        type=int,
        default=3,
        help="Run /progress/load every N save calls; 0 disables load calls",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    worker_steps = [int(x.strip()) for x in args.workers_steps.split(",") if x.strip()]

    print(f"Base URL: {args.base_url}")
    print(f"User: {args.username}, difficulty: {args.difficulty}")
    print(f"Steps: {worker_steps}, duration per step: {args.duration}s")
    print(f"Per-worker save pause: {args.save_pause}s, load every: {args.load_every}")

    all_reports = []
    for workers in worker_steps:
        report = run_step(
            base_url=args.base_url,
            username=args.username,
            workers=workers,
            difficulty=args.difficulty,
            run_seconds=args.duration,
            save_pause_s=args.save_pause,
            load_every_n=args.load_every,
        )
        print_report(report)
        all_reports.append(report)

    print("\n=== Compact summary ===")
    for r in all_reports:
        if r.get("total_requests", 0) == 0:
            print(f"workers={r['workers']:>3} | no data")
            continue
        status_counts = r["status_counts"]
        failures = sum(v for k, v in status_counts.items() if k not in (200, 429))
        print(
            f"workers={r['workers']:>3} | rps={r['rps']:.1f} | "
            f"p95={r['latency_ms']['p95']}ms | p99={r['latency_ms']['p99']}ms | "
            f"non-200/429={failures}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
