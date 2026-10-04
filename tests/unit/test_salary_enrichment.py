"""Pay in the dashboard data: midpoint of ranges, recovery from the description,
hourly rates annualized from the posting's own hours, and stale adjusted values."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from generate_dashboard_analytics import (  # noqa: E402
    enrich_compensation_fields,
    row_salary,
)

HEADER = "Hours per Week:\n{hours}\nSalary:\n{salary}\nDescription\n{prose}"


def enrich(row):
    rows = [{"location": "Lincoln, Nebraska", **row}]
    enrich_compensation_fields(rows)
    return rows[0]


def test_range_is_stored_as_min_max_and_midpoint():
    out = enrich({"salary": "$24,500 to $27,500 per year"})
    assert (out["salary_min"], out["salary_max"]) == (24500.0, 27500.0)
    assert out["salary_annualized"] == 26000.0
    assert out["salary_is_range"] is True
    assert out["salary_source"] == "salary field"


def test_floor_is_flagged():
    out = enrich({"salary": "starting at $14,000 per year"})
    assert out["salary_is_floor"] is True


def test_salary_missing_from_field_is_recovered_from_description():
    page = HEADER.format(
        hours="20", salary="none", prose="Stipend of $21,500 per year."
    )
    out = enrich({"salary": "", "description": page})
    assert out["salary_annualized"] == 21500.0
    assert out["salary_source"] == "description text"


def test_commensurate_salary_is_not_recovered_from_description():
    page = HEADER.format(
        hours="20", salary="x", prose="Travel funds of $1,200 per year."
    )
    out = enrich({"salary": "Commensurate", "description": page})
    assert "salary_annualized" not in out


def test_hourly_rate_uses_the_postings_hours_per_week_header():
    page = HEADER.format(hours="20 - 40", salary="$20 per hour", prose="")
    out = enrich({"salary": "$20 per hour", "description": page})
    assert out["salary_annualized"] == 20 * 30 * 52


def test_stale_adjusted_value_from_an_older_parser_is_recomputed():
    # Adjusted value was computed from the old lower-bound figure ($24,500 / 0.9).
    out = enrich(
        {
            "salary": "$24,500 to $27,500 per year",
            "cost_of_living_index": 0.9,
            "salary_lincoln_adjusted": round(24500 / 0.9, 2),
            "salary_adjustment_source": "analytics_backfill",
        }
    )
    assert out["salary_lincoln_adjusted"] == round(26000 / 0.9, 2)


def test_aggregates_read_the_enriched_value_so_recovered_salaries_count():
    assert row_salary({"salary": "", "salary_annualized": 21500.0}) == 21500.0
    assert row_salary({"salary": "$25,000 per year"}) == 25000.0
    assert row_salary({"salary": "Commensurate"}) is None
