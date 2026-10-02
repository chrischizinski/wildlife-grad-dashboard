"""Health checks exist so a silent bad scrape fails loudly instead of shipping."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from check_scrape_health import (  # noqa: E402
    check_freshness,
    check_guard,
    count_positions,
)

NOW = datetime(2026, 10, 2, tzinfo=timezone.utc)


def test_empty_scrape_fails_even_with_no_history():
    assert check_guard(0, None)


def test_shrinking_dataset_fails():
    # A site layout change that drops most rows must not be committed.
    assert check_guard(100, 436)


def test_normal_weekly_growth_passes():
    assert check_guard(474, 436) == []


def test_small_dedup_shrink_is_tolerated():
    # Dedup can legitimately remove a few rows; do not alert on that.
    assert check_guard(430, 436) == []


def test_count_positions_handles_both_shapes():
    assert count_positions({"positions": [1, 2, 3]}) == 3
    assert count_positions([1, 2]) == 2
    assert count_positions({"positions": None}) == 0


def test_stale_data_fails_and_fresh_data_passes():
    old = (NOW - timedelta(days=11)).isoformat()
    recent = (NOW - timedelta(days=6)).isoformat()
    assert check_freshness(old, NOW, 10)
    assert check_freshness(recent, NOW, 10) == []


def test_missing_or_garbage_timestamp_fails():
    assert check_freshness(None, NOW, 10)
    assert check_freshness("not-a-date", NOW, 10)
