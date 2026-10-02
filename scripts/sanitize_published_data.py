#!/usr/bin/env python3
"""
Remove personal fields from data files that are published with the dashboard.

Contact details scraped from job postings (e.g. faculty email addresses) must
not be republished in the files served from GitHub Pages or offered as
downloads: the contact_info field is dropped and email addresses inside any
text field (description, requirements, ...) are redacted.

Usage: sanitize_published_data.py PATH [PATH ...]
Rewrites each JSON file (or every *.json under a directory) that carries private data.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

SRC_ROOT = Path(__file__).resolve().parent.parent / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from wildlife_grad.utils.privacy import redact_emails  # noqa: E402

PRIVATE_FIELDS = frozenset({"contact_info"})


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_emails(value)
    if isinstance(value, list):
        return [_redact_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _redact_value(v) for k, v in value.items()}
    return value


def strip_private_fields_from_rows(rows: List[Any]) -> List[Any]:
    """Drop private fields and redact email addresses in every text value."""
    return [
        {k: _redact_value(v) for k, v in row.items() if k not in PRIVATE_FIELDS}
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


def sanitize_file(path: Path) -> bool:
    """Rewrite a JSON file if it carries private fields or emails."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    cleaned = strip_private_fields(payload)
    if cleaned == payload:
        return False
    path.write_text(json.dumps(cleaned, indent=2, ensure_ascii=False), encoding="utf-8")
    return True


def sanitize_directory(directory: Path) -> List[Path]:
    """Rewrite JSON files under directory that contain private data."""
    return [path for path in sorted(directory.rglob("*.json")) if sanitize_file(path)]


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    for arg in sys.argv[1:]:
        target = Path(arg)
        changed = [target] if target.is_file() and sanitize_file(target) else []
        if target.is_dir():
            changed = sanitize_directory(target)
        for path in changed:
            print(f"sanitized: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
