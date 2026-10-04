"""The scraper stores the whole page as `description`; the header block must be
readable without a re-scrape."""

from wildlife_grad.utils.posting_text import header_field, posting_prose

PAGE = """MS Assistantship: Bat ecology
Texas State University (State)
Details
Application Deadline:
05/01/2026
Published:
11/03/2025
Hours per Week:
28 - 40
Salary:
$5,000 to $6,000 per year
Education Required:
Masters
Tags:
Graduate Opportunities
Description
 Stipend of $21,500 per year plus tuition.
"""


def test_reads_labelled_header_values():
    assert header_field(PAGE, "Hours per Week") == "28 - 40"
    assert header_field(PAGE, "Education Required") == "Masters"
    assert header_field(PAGE, "Salary") == "$5,000 to $6,000 per year"


def test_missing_or_blank_label_returns_none():
    assert header_field(PAGE, "Ending Date") is None
    assert header_field(None, "Salary") is None
    assert header_field("Salary:\n\nDescription\n", "Salary") is None


def test_prose_starts_after_description_heading():
    prose = posting_prose(PAGE)
    assert prose.strip().startswith("Stipend of $21,500")
    assert "Hours per Week" not in prose


def test_prose_without_heading_is_the_whole_text():
    assert posting_prose("just text") == "just text"
    assert posting_prose(None) == ""
