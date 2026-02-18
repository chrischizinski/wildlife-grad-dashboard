#!/usr/bin/env python3
"""Regression check for known non-graduate title leakage in dashboard-facing data."""

from __future__ import annotations

import json
import sys
from pathlib import Path

TARGET_FILE = Path("web/data/verified_graduate_assistantships.json")
LEAKAGE_TITLES = [
    "Environmental Field Technician",
    "Environmental Specialist (Rapid Responder)",
    "Fish Passage Biologist I",
    "Archaeologist",
    "Associate Veterinarian",
]


def load_rows(path: Path) -> list[dict]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        positions = obj.get("positions")
        if isinstance(positions, list):
            return positions
    return []


def main() -> int:
    if not TARGET_FILE.exists():
        print(f"ERROR: Missing file: {TARGET_FILE}")
        print("Generate/copy dashboard data first, then re-run this check.")
        return 2

    rows = load_rows(TARGET_FILE)
    matched: list[str] = []
    for row in rows:
        title = str(row.get("title", "")).strip().lower()
        if not title:
            continue
        for blocked in LEAKAGE_TITLES:
            if blocked.lower() in title:
                matched.append(str(row.get("title", "")).strip())
                break

    if matched:
        print("FAIL: Found leakage titles in dashboard-facing graduate listings:")
        for title in matched:
            print(f"- {title}")
        return 1

    print(f"PASS: No leakage titles found in {TARGET_FILE} ({len(rows)} rows checked).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
