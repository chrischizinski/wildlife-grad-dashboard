"""Published data must not republish scraped contact details, and salary
statistics must describe the U.S. market only."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from generate_dashboard_analytics import calculate_analytics  # noqa: E402
from sanitize_published_data import (  # noqa: E402
    sanitize_directory,
    strip_private_fields,
)


def row(**overrides):
    base = {
        "title": "MS Assistantship",
        "organization": "Univ",
        "discipline_primary": "Wildlife",
        "salary": "$25,000 per year",
        "is_us_mappable": True,
        "contact_info": "someone@example.edu",
    }
    base.update(overrides)
    return base


def test_contact_info_removed_from_row_list_but_other_fields_kept():
    cleaned = strip_private_fields([row()])
    assert "contact_info" not in cleaned[0]
    assert cleaned[0]["title"] == "MS Assistantship"


def test_contact_info_removed_from_positions_dict_shape():
    cleaned = strip_private_fields({"metadata": {"n": 1}, "positions": [row()]})
    assert "contact_info" not in cleaned["positions"][0]
    assert cleaned["metadata"] == {"n": 1}


def test_sanitize_directory_rewrites_only_files_with_private_fields(tmp_path):
    dirty = tmp_path / "dirty.json"
    clean = tmp_path / "clean.json"
    dirty.write_text(json.dumps([row()]))
    clean.write_text(json.dumps([{"title": "x"}]))
    before = clean.read_text()

    changed = sanitize_directory(tmp_path)

    assert changed == [dirty]
    assert "contact_info" not in dirty.read_text()
    assert clean.read_text() == before


def test_non_us_salaries_excluded_from_salary_statistics():
    rows = [
        row(salary="$30,000 per year"),
        row(salary="$5,000 per year", is_us_mappable=False),  # e.g. Beijing
        row(salary="$5,000 per year", is_us_mappable=False),
    ]
    stats = calculate_analytics(rows)["top_disciplines"]["Wildlife"][
        "salary_stats_nominal"
    ]
    assert stats["count"] == 1
    assert stats["median"] == 30000


def test_rows_without_us_flag_still_count_for_salary():
    # Older rows predate the flag; absence must not silently drop them.
    r = row(salary="$28,000 per year")
    del r["is_us_mappable"]
    stats = calculate_analytics([r])["top_disciplines"]["Wildlife"][
        "salary_stats_nominal"
    ]
    assert stats["count"] == 1
