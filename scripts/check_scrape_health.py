#!/usr/bin/env python3
"""
Health checks for the weekly scrape pipeline. Exit code 1 means "fail loudly".

Modes:
- guard:     the cumulative dataset must not shrink or come back empty after a
             scrape (a broken selector or site change would otherwise commit
             an empty week silently).
- freshness: dashboard_analytics.json must have been updated recently (catches
             a scheduled run that never fired).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENHANCED_PATH = "data/enhanced_data.json"
ANALYTICS_PATH = PROJECT_ROOT / "web" / "data" / "dashboard_analytics.json"
MAX_SHRINK_FRACTION = 0.10
DEFAULT_MAX_AGE_DAYS = 10


def count_positions(payload: Any) -> int:
    if isinstance(payload, dict):
        payload = payload.get("positions", [])
    return len(payload) if isinstance(payload, list) else 0


def check_guard(new_count: int, previous_count: Optional[int]) -> List[str]:
    """Return problems; empty list means healthy."""
    problems = []
    if new_count == 0:
        problems.append("dataset has 0 positions after scrape")
    if previous_count:
        floor = previous_count * (1 - MAX_SHRINK_FRACTION)
        if new_count < floor:
            problems.append(
                f"dataset shrank from {previous_count} to {new_count} positions "
                f"(more than {MAX_SHRINK_FRACTION:.0%} drop)"
            )
    return problems


def check_freshness(
    last_updated: Optional[str], now: datetime, max_age_days: int
) -> List[str]:
    if not last_updated:
        return ["dashboard_analytics.json has no last_updated"]
    try:
        stamp = datetime.fromisoformat(str(last_updated).replace("Z", "+00:00"))
    except ValueError:
        return [f"unparseable last_updated: {last_updated!r}"]
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    age_days = (now - stamp).total_seconds() / 86400
    if age_days > max_age_days:
        return [f"data is {age_days:.1f} days old (limit {max_age_days})"]
    return []


def previous_count_from_git() -> Optional[int]:
    result = subprocess.run(
        ["git", "show", f"HEAD:{ENHANCED_PATH}"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return count_positions(json.loads(result.stdout))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("mode", choices=["guard", "freshness"])
    parser.add_argument("--max-age-days", type=int, default=DEFAULT_MAX_AGE_DAYS)
    args = parser.parse_args()

    if args.mode == "guard":
        path = PROJECT_ROOT / ENHANCED_PATH
        if not path.exists():
            problems = [f"{ENHANCED_PATH} is missing after scrape"]
        else:
            new_count = count_positions(json.loads(path.read_text(encoding="utf-8")))
            previous = previous_count_from_git()
            print(f"positions: previous={previous} new={new_count}")
            problems = check_guard(new_count, previous)
    else:
        payload = json.loads(ANALYTICS_PATH.read_text(encoding="utf-8"))
        problems = check_freshness(
            payload.get("last_updated"), datetime.now(timezone.utc), args.max_age_days
        )

    for problem in problems:
        print(f"::error::{problem}")
    if not problems:
        print(f"{args.mode} check OK")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
