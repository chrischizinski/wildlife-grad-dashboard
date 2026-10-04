"""Split a scraped posting page into its labelled header fields and prose.

The scraper stores the whole page text as ``description``. That text begins with a
labelled block, for example::

    Hours per Week:
    28 - 40
    Salary:
    $5,000 to $6,000 per year
    Education Required:
    Masters
    ...
    Description
    <prose>

These helpers read the block without needing a re-scrape.
"""

from __future__ import annotations

import re
from typing import Optional


def header_field(page_text: Optional[str], label: str) -> Optional[str]:
    """Value on the line after ``"<label>:"``, or None when absent or blank."""
    if not page_text:
        return None
    match = re.search(
        rf"^{re.escape(label)}:[ \t]*\n([^\n]*)", page_text, flags=re.MULTILINE
    )
    value = match.group(1).strip() if match else ""
    return value or None


def posting_prose(page_text: Optional[str]) -> str:
    """Text after the ``Description`` heading; the whole text if there is none."""
    if not page_text:
        return ""
    match = re.search(r"^Description[ \t]*\n", page_text, flags=re.MULTILINE)
    return page_text[match.end() :] if match else page_text
