"""The weekly Discord summary must survive the timestamps actually published.

dashboard_positions.json mixes timezone-aware scrape timestamps with naive ones
from older history rows. Comparing the two raised TypeError and killed the
summary step on 2026-11-11 (run 43085515051), right after #26 started serving
those history rows.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from send_discord_weekly_summary import (  # noqa: E402
    build_message,
    latest_capture_rows,
    parse_iso_datetime,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

OLD_NAIVE = {
    "title": "MS Assistantship (2025 history row)",
    "scrape_run_id": "old-run",
    "scraped_at": "2025-07-13T17:53:56.605240",
    "published_date": "06/10/2025",
}
NEW_AWARE = {
    "title": "PhD Assistantship (this week)",
    "scrape_run_id": "new-run",
    "scraped_at": "2026-11-11T19:18:15+00:00",
    "published_date": "11/10/2026",
}


def test_mixed_naive_and_aware_rows_pick_the_latest_run():
    # Must not raise, and the newest capture must still win.
    rows = latest_capture_rows([OLD_NAIVE, NEW_AWARE])
    assert [r["scrape_run_id"] for r in rows] == ["new-run"]


def test_every_parsed_value_is_timezone_aware():
    for value in ("2025-07-13T17:53:56", "2026-11-11T19:18:15Z", "06/10/2025"):
        assert parse_iso_datetime(value).tzinfo is not None, value


def test_summary_builds_from_the_published_files():
    # The files the workflow step reads, as committed.
    positions = json.loads(
        (REPO_ROOT / "web/data/dashboard_positions.json").read_text(encoding="utf-8")
    )
    analytics = json.loads(
        (REPO_ROOT / "web/data/dashboard_analytics.json").read_text(encoding="utf-8")
    )
    rows = (
        positions.get("positions", positions)
        if isinstance(positions, dict)
        else positions
    )
    assert build_message(rows, analytics)
