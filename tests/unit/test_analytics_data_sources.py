"""Which files feed the published dashboard rows.

web/data/enhanced_data.json is a 2025 leftover that nothing writes. It used to be
merged last, so its URL-less rows tied with current historical rows in dedup and
silently replaced them (issue #25). Current data must win.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from generate_dashboard_analytics import load_and_merge_data  # noqa: E402

ROW = {
    "title": "MS Assistantship in Fisheries Ecology",
    "organization": "Example University",
    "url": "",
    "is_graduate_position": True,
}


def write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_leftover_enhanced_file_cannot_replace_current_rows(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write(
        tmp_path / "data/historical_positions.json", [{**ROW, "first_seen": "current"}]
    )
    write(
        tmp_path / "web/data/enhanced_data.json",
        {"positions": [{**ROW, "first_seen": "stale-2025"}]},
    )

    rows = [r for r in load_and_merge_data() if r.get("title") == ROW["title"]]

    assert len(rows) == 1
    assert rows[0]["first_seen"] == "current"


def test_leftover_enhanced_file_adds_no_rows(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write(tmp_path / "data/historical_positions.json", [ROW])
    write(
        tmp_path / "web/data/enhanced_data.json",
        [{**ROW, "title": "PhD Assistantship in Waterfowl Ecology"}],
    )

    titles = {r.get("title") for r in load_and_merge_data()}

    assert "PhD Assistantship in Waterfowl Ecology" not in titles
