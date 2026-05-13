#!/usr/bin/env python3
"""Delete load-test users (default prefix loaduser_) and CASCADE-linked rows from SQLite."""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path


def default_db_candidates() -> list[Path]:
    env = os.environ.get("SQLITE_DB_PATH", "").strip()
    paths: list[Path] = []
    if env:
        paths.append(Path(env).expanduser())
    here = Path(__file__).resolve().parent
    paths.append(here.parent / "black-white-pic" / "data" / "nonogram.db")
    return paths


def resolve_db_path(explicit: str | None) -> Path | None:
    if explicit:
        p = Path(explicit).expanduser()
        return p if p.is_file() else None
    for p in default_db_candidates():
        if p.is_file():
            return p
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Remove users created by load_test.py (username LIKE prefix%)"
    )
    parser.add_argument(
        "--db-path",
        help="SQLite database path (or set SQLITE_DB_PATH)",
    )
    parser.add_argument(
        "--prefix",
        default="loaduser_",
        help="Username prefix to delete (default: loaduser_)",
    )
    args = parser.parse_args()

    db_path = resolve_db_path(args.db_path)
    if db_path is None:
        print(
            "Database not found. Pass --db-path or set SQLITE_DB_PATH "
            "(or place black-white-pic/data/nonogram.db next to this repo).",
            file=sys.stderr,
        )
        return 1

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()
    pattern = args.prefix + "%"
    cur.execute("SELECT id, username FROM users WHERE username LIKE ?", (pattern,))
    rows = cur.fetchall()
    if not rows:
        print(f"No users matching username LIKE {pattern!r} in {db_path}")
        conn.close()
        return 0

    cur.execute("DELETE FROM users WHERE username LIKE ?", (pattern,))
    deleted = cur.rowcount
    conn.commit()
    conn.close()

    print(f"Deleted {deleted} user(s) from {db_path}:")
    for uid, name in rows:
        print(f"  - id={uid} username={name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
