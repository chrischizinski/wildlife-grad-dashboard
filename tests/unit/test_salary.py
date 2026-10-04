"""Tests for the salary parser.

Cases come from an audit of real postings against the earlier parser, which took the
lower bound of a posted range and dropped hourly rates and description-only salaries.
"""

import pytest

from wildlife_grad.utils.salary import (
    find_salary_phrase,
    parse_hours_per_week,
    parse_salary,
)


class TestRanges:
    """A posted range keeps both ends; the midpoint is what summaries use."""

    def test_annual_range_keeps_min_max_and_midpoint(self):
        parsed = parse_salary("$24,500 to $27,500 per year")
        assert (parsed.annual_min, parsed.annual_max) == (24500.0, 27500.0)
        assert parsed.annual_mid == 26000.0
        assert parsed.is_range

    def test_monthly_range_is_annualized_before_averaging(self):
        parsed = parse_salary("$1,888 to $2,388 per month")
        assert parsed.annual_min == 22656.0
        assert parsed.annual_max == 28656.0
        assert parsed.annual_mid == 25656.0

    def test_single_amount_is_not_a_range(self):
        parsed = parse_salary("$25,000 per year")
        assert parsed.annual_mid == 25000.0
        assert not parsed.is_range

    def test_extra_numbers_do_not_pull_the_minimum_down(self):
        # The old parser took min() over every number, including "12" here.
        parsed = parse_salary("$20,000 to $25,000 for 12 months")
        assert (parsed.annual_min, parsed.annual_max) == (20000.0, 25000.0)

    def test_from_is_a_range_not_a_floor(self):
        parsed = parse_salary("from $20,000 to $26,000 per year")
        assert parsed.is_range
        assert not parsed.is_floor


class TestFloors:
    """'Starting at' is a minimum, not a typical offer, and must be flagged."""

    @pytest.mark.parametrize(
        "text", ["starting at $14,000 per year", "at least $20,000", "minimum $18,000"]
    )
    def test_floor_phrases_are_flagged(self, text):
        assert parse_salary(text).is_floor

    def test_plain_amount_is_not_a_floor(self):
        assert not parse_salary("$21,500 per year").is_floor


class TestUnits:
    def test_monthly_assumes_twelve_months(self):
        assert parse_salary("$2,000 per month").annual_mid == 24000.0

    def test_weekly(self):
        assert parse_salary("$600 per week").annual_mid == 31200.0

    def test_hourly_with_hours_in_text(self):
        parsed = parse_salary("$15 per hour, 20 hours per week")
        assert parsed.annual_mid == 15 * 20 * 52

    def test_hourly_uses_hours_per_week_argument(self):
        # Old parser returned nothing here; the posting's own hours field supplies them.
        parsed = parse_salary("starting at $18 per hour", hours_per_week=20)
        assert parsed.annual_mid == 18 * 20 * 52
        assert parsed.is_floor

    def test_hourly_without_hours_has_no_value(self):
        parsed = parse_salary("$15 per hour")
        assert not parsed.has_value
        assert parsed.period == "hour"

    def test_long_term_is_not_a_semester_rate(self):
        assert parse_salary("$20,000 long-term funding").annual_mid == 20000.0


class TestNoValue:
    @pytest.mark.parametrize(
        "text", ["Commensurate / Negotiable", "none", "N/A", "Competitive", "TBD"]
    )
    def test_non_numeric_text_is_flagged_and_has_no_value(self, text):
        parsed = parse_salary(text)
        assert parsed.is_non_numeric
        assert not parsed.has_value

    @pytest.mark.parametrize("text", [None, "", "   "])
    def test_empty_input_has_no_value(self, text):
        parsed = parse_salary(text)
        assert not parsed.has_value
        assert not parsed.is_non_numeric

    def test_out_of_range_amount_is_rejected(self):
        assert not parse_salary("$50 per year").has_value
        assert not parse_salary("$900,000 per year").has_value


class TestRecoveryFromDescription:
    """Salary missing from the salary field can sit in the description prose."""

    @pytest.mark.parametrize(
        "prose, expected",
        [
            ("Stipend of $21,500 per year plus tuition.", "$21,500 per year"),
            ("pays $23,500 to $26,500 per year", "$23,500 to $26,500 per year"),
            ("starting at $20 per hour", "starting at $20 per hour"),
        ],
    )
    def test_finds_salary_phrase(self, prose, expected):
        assert find_salary_phrase(prose) == expected

    def test_recovered_phrase_parses(self):
        phrase = find_salary_phrase("Stipend: $23,500 to $26,500 per year.")
        assert parse_salary(phrase).annual_mid == 25000.0

    def test_no_phrase_returns_none(self):
        assert find_salary_phrase("Competitive stipend and tuition waiver.") is None
        assert find_salary_phrase(None) is None


class TestHoursPerWeek:
    """The posting's Hours per Week field is text such as '20 - 40' or 'at least 40'."""

    @pytest.mark.parametrize(
        "text, expected",
        [("20 - 40", 30.0), ("at least 40", 40.0), ("at most 20", 20.0), ("37", 37.0)],
    )
    def test_parses_ranges_and_bounds(self, text, expected):
        assert parse_hours_per_week(text) == expected

    @pytest.mark.parametrize("text", [None, "", "0", "varies", "400"])
    def test_unusable_values_return_none(self, text):
        assert parse_hours_per_week(text) is None
