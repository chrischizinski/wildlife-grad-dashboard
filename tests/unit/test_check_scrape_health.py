"""Health checks exist so a silent bad scrape fails loudly instead of shipping."""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from check_scrape_health import (  # noqa: E402
    BATCH_PATH,
    CUMULATIVE_PATH,
    check_batch,
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


def test_guard_reads_files_the_scraper_actually_writes(tmp_path, monkeypatch):
    # The guard once read data/enhanced_data.json, which nothing writes; it
    # compared a frozen file with itself every week and could never fail.
    # Run the scraper's real save step and require it to produce both files
    # the guard inspects, so the two can never drift apart silently again.
    from wildlife_job_scraper import JobListing, ScraperConfig, WildlifeJobScraper

    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    scraper = WildlifeJobScraper(
        ScraperConfig(output_dir=tmp_path, log_file=str(tmp_path / "scrape.log"))
    )
    job = JobListing(
        title="MS Assistantship in Wildlife Ecology",
        url="https://example.org/job/1",
        is_graduate_position=True,
        grad_confidence=0.9,
    )
    scraper.save_graduate_positions_only([job])

    for rel_path in (CUMULATIVE_PATH, BATCH_PATH):
        written = tmp_path / rel_path
        assert written.exists(), f"scraper did not write {rel_path}"
        assert count_positions(json.loads(written.read_text())) == 1


def test_scraper_that_wrote_nothing_fails():
    # When the scraper finds 0 jobs it skips every write, so the batch file is
    # still last week's committed (non-empty) copy. Its count alone looks fine.
    assert check_batch(batch_count=11, rewritten=False)


def test_empty_weekly_batch_fails():
    # Lowest observed week was 11; a 0 almost certainly means a broken selector.
    assert check_batch(batch_count=0, rewritten=True)


def test_normal_weekly_batch_passes():
    assert check_batch(batch_count=11, rewritten=True) == []
