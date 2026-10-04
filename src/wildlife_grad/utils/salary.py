"""Salary parsing for assistantship postings.

Postings state pay as free text ("$24,500 to $27,500 per year", "starting at $18
per hour", "$2,000 per month"). ``parse_salary`` turns that text into annualized
minimum, maximum and midpoint values and records how the number was read, so a
single posting can be summarised however an analysis needs (midpoint is the
dashboard default).

Conventions, all recorded on the result so they can be audited later:

- A posted range keeps both ends; the midpoint is their average.
- "starting at $X" (and "at least", "minimum") is a floor, not a typical offer.
- Monthly rates assume 12 months; hourly rates need hours per week.
- Amounts that annualize outside ``MIN_ANNUAL``..``MAX_ANNUAL`` are rejected.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

PARSER_VERSION = "2"

MIN_ANNUAL = 1_000.0
MAX_ANNUAL = 300_000.0

_NON_NUMERIC_PHRASES = (
    "commensurate",
    "negotiable",
    "competitive",
    "none",
    "n/a",
    "depends on",
    "varies",
    "tbd",
    "to be determined",
)

_DOLLAR_AMOUNT = re.compile(r"\$\s*(\d[\d,]*(?:\.\d+)?)\s*([kK]?)")
# Without a "$" sign: "25,000", "25000", "25k". Plain small numbers ("20 hours")
# are not treated as pay.
_BARE_AMOUNT = re.compile(
    r"(?<![\d.])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d{4,7}(?:\.\d+)?)\s*([kK]?)"
)
_RANGE_WORDS = re.compile(r"\bbetween\b|\bto\b|\bup to\b|[-–—]")
_FLOOR_WORDS = re.compile(r"starting at|starts at|at least|minimum")

# Phrase used to recover a salary that sits in the description prose when the
# salary field itself is empty: "$X [to $Y] per <unit>".
_SALARY_PHRASE = re.compile(
    r"(?:starting at\s*)?\$\s*\d[\d,]*(?:\.\d+)?"
    r"(?:\s*(?:to|-)\s*\$\s*\d[\d,]*(?:\.\d+)?)?"
    r"\s*(?:per|/)\s*(?:year|month|hour|hr|week)",
    re.IGNORECASE,
)

_HOURLY_HOURS = re.compile(
    r"(\d{1,2}(?:\.\d+)?)\s*(?:hours?|hrs?)\s*(?:/|\s+per\s+)?\s*(?:week|wk)\b"
)


@dataclass(frozen=True)
class SalaryParse:
    """Result of parsing one salary string. Annual fields are in US dollars."""

    annual_min: Optional[float] = None
    annual_max: Optional[float] = None
    annual_mid: Optional[float] = None
    period: Optional[str] = None
    is_range: bool = False
    is_floor: bool = False
    is_non_numeric: bool = False
    parser_version: str = PARSER_VERSION

    @property
    def has_value(self) -> bool:
        return self.annual_mid is not None


def _period_multiplier(text: str) -> tuple[Optional[str], Optional[float]]:
    """Return (period, annualizing multiplier) for the unit named in ``text``."""
    if re.search(r"\b(hour|hourly|hr|hrs)\b|/hr", text):
        return "hour", None  # needs hours per week
    if re.search(r"\b(bi-?week|fortnight)", text):
        return "biweek", 26.0
    if re.search(r"\b(week|wk)\b|/wk", text):
        return "week", 52.0
    if re.search(r"\b(day|daily)\b|/day", text):
        return "day", 260.0
    if re.search(r"\b(month|mo)\b|/mo", text):
        return "month", 12.0
    if re.search(r"\bsemester\b|per term", text):
        return "semester", 2.0
    return "year", 1.0


def _amounts(salary_str: str) -> list[float]:
    """Dollar amounts in the text; falls back to bare numbers when no "$" is used."""
    found = _DOLLAR_AMOUNT.findall(salary_str)
    if not found:
        found = _BARE_AMOUNT.findall(salary_str)
    values = []
    for raw, k_suffix in found:
        try:
            value = float(raw.replace(",", ""))
        except ValueError:
            continue
        if k_suffix:
            value *= 1000.0
        if value > 0:
            values.append(value)
    return values


def parse_salary(
    salary_str: Optional[str], hours_per_week: Optional[float] = None
) -> SalaryParse:
    """Parse a posted salary string into annualized min / max / midpoint.

    Args:
        salary_str: Salary text from the posting.
        hours_per_week: Weekly hours, used only to annualize hourly rates when the
            text itself does not state them.

    Returns:
        A ``SalaryParse``. ``has_value`` is False when no usable number exists
        (non-numeric text, an unannualizable hourly rate, or an out-of-range value).
    """
    if not salary_str or not salary_str.strip():
        return SalaryParse()

    text = salary_str.lower().strip()
    if text in {"n/a", "unknown", "none"} or any(
        phrase in text for phrase in _NON_NUMERIC_PHRASES
    ):
        return SalaryParse(is_non_numeric=True)

    period, multiplier = _period_multiplier(text)
    if period == "hour":
        hours_match = _HOURLY_HOURS.search(text)
        hours = float(hours_match.group(1)) if hours_match else hours_per_week
        if not hours or hours <= 0:
            return SalaryParse(period=period)
        multiplier = hours * 52.0

    amounts = _amounts(salary_str)
    if not amounts or multiplier is None:
        return SalaryParse(period=period)

    is_range = len(amounts) >= 2 and bool(_RANGE_WORDS.search(text))
    low, high = (min(amounts), max(amounts)) if is_range else (amounts[0], amounts[0])
    annual_min, annual_max = low * multiplier, high * multiplier

    if not (MIN_ANNUAL <= annual_min and annual_max <= MAX_ANNUAL):
        return SalaryParse(period=period)

    return SalaryParse(
        annual_min=round(annual_min, 2),
        annual_max=round(annual_max, 2),
        annual_mid=round((annual_min + annual_max) / 2, 2),
        period=period,
        is_range=is_range,
        is_floor=bool(_FLOOR_WORDS.search(text)),
    )


def find_salary_phrase(prose: Optional[str]) -> Optional[str]:
    """First "$X [to $Y] per <unit>" phrase in free text, or None."""
    if not prose:
        return None
    match = _SALARY_PHRASE.search(prose)
    return match.group(0) if match else None


def parse_hours_per_week(value: Optional[object]) -> Optional[float]:
    """Hours per week from posting text such as "20 - 40", "at least 40" or "37".

    A range becomes its midpoint; a bound ("at least 40", "at most 20") becomes the
    stated number. Zero, missing or implausible values return None.
    """
    if value is None:
        return None
    numbers = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", str(value))[:2]]
    if not numbers:
        return None
    hours = sum(numbers) / len(numbers)
    return hours if 1 <= hours <= 80 else None
