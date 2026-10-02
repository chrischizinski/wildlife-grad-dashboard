#!/usr/bin/env python3
"""
Remove personal fields from data files that are published with the dashboard.

Contact details scraped from job postings (e.g. faculty email addresses) are
kept in the raw pipeline data but must not be republished in the files served
from GitHub Pages or offered as downloads.

Usage: sanitize_published_data.py DIR [DIR ...]
Rewrites every *.json file under each DIR that carries a private field.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

PRIVATE_FIELDS = frozenset({"contact_info"})


def strip_private_fields_from_rows(rows: List[Any]) -> List[Any]:
    return [
        {k: v for k, v in row.items() if k not in PRIVATE_FIELDS}
        if isinstance(row, dict)
        else row
        for row in rows
    ]


def strip_private_fields(payload: Any) -> Any:
    """Return payload without private fields on its position rows.

    Handles the two shapes used by published files: a list of rows, or a dict
    holding the rows under "positions". Anything else is returned unchanged.
    """
    if isinstance(payload, list):
        return strip_private_fields_from_rows(payload)
    if isinstance(payload, dict) and isinstance(payload.get("positions"), list):
        cleaned: Dict[str, Any] = dict(payload)
        cleaned["positions"] = strip_private_fields_from_rows(payload["positions"])
        return cleaned
    return payload


def sanitize_directory(directory: Path) -> List[Path]:
    """Rewrite JSON files in directory that contain private fields."""
    changed: List[Path] = []
    for path in sorted(directory.rglob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        cleaned = strip_private_fields(payload)
        if cleaned != payload:
            path.write_text(
                json.dumps(cleaned, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            changed.append(path)
    return changed


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    for arg in sys.argv[1:]:
        for path in sanitize_directory(Path(arg)):
            print(f"sanitized: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
