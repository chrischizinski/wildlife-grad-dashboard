#!/usr/bin/env python3
"""
Health checks for the weekly scrape pipeline. Exit code 1 means "fail loudly".

Modes:
- guard:     after a scrape, (1) the cumulative dataset must not shrink or come
             back empty, and (2) the scraper must have written a non-empty
             weekly batch. A broken selector or site change would otherwise
             commit an empty week silently: when the scraper finds 0 jobs it
             writes nothing, so the cumulative file just stays the same size.
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
# Both files are written by src/wildlife_grad/scraper/wildlife_job_scraper.py.
# (The guard previously read data/enhanced_data.json, which nothing writes, so
# it compared a frozen file with itself and could never fail.)
CUMULATIVE_PATH = "data/historical_positions.json"
BATCH_PATH = "data/processed/verified_graduate_assistantships.json"
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


def check_batch(batch_count: int, rewritten: bool) -> List[str]:
    """Problems with this run's weekly batch; empty list means healthy.

    `rewritten` is False when the batch file is byte-identical to the committed
    version, i.e. the scraper did not write it this run (it skips all writes
    when it finds 0 jobs).
    """
    if not rewritten:
        return [
            f"{BATCH_PATH} was not rewritten this run (scraper likely found 0 jobs)"
        ]
    if batch_count == 0:
        return ["scraper found 0 new graduate positions this week"]
    return []


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


def committed_text(rel_path: str) -> Optional[str]:
    """The file's content at HEAD, or None if it is not committed."""
    result = subprocess.run(
        ["git", "show", f"HEAD:{rel_path}"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    return result.stdout if result.returncode == 0 else None


def run_guard() -> List[str]:
    problems: List[str] = []

    cumulative = PROJECT_ROOT / CUMULATIVE_PATH
    if not cumulative.exists():
        problems.append(f"{CUMULATIVE_PATH} is missing after scrape")
    else:
        new_count = count_positions(json.loads(cumulative.read_text(encoding="utf-8")))
        committed = committed_text(CUMULATIVE_PATH)
        previous = count_positions(json.loads(committed)) if committed else None
        print(f"cumulative positions: previous={previous} new={new_count}")
        problems.extend(check_guard(new_count, previous))

    batch = PROJECT_ROOT / BATCH_PATH
    if not batch.exists():
        problems.append(f"{BATCH_PATH} is missing after scrape")
    else:
        text = batch.read_text(encoding="utf-8")
        batch_count = count_positions(json.loads(text))
        rewritten = text != committed_text(BATCH_PATH)
        print(f"weekly batch: positions={batch_count} rewritten={rewritten}")
        problems.extend(check_batch(batch_count, rewritten))

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("mode", choices=["guard", "freshness"])
    parser.add_argument("--max-age-days", type=int, default=DEFAULT_MAX_AGE_DAYS)
    args = parser.parse_args()

    if args.mode == "guard":
        problems = run_guard()
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
