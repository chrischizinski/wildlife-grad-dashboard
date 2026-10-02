"""The validation sample must be blind and the estimator statistically correct;
otherwise the accuracy number it reports is meaningless."""

import csv
import json
import sys
from argparse import Namespace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from discipline_validation import (  # noqa: E402
    SAMPLE_COLUMNS,
    cmd_sample,
    draw_sample,
    normalize_answer,
    score,
    stratified_accuracy,
    wilson,
)


def make_rows():
    rows = []
    for i in range(40):
        rows.append({"url": f"u/w{i}", "title": f"w{i}", "discipline_primary": "Wildlife"})
    for i in range(30):
        rows.append({"url": f"u/f{i}", "title": f"f{i}", "discipline_primary": "Fisheries and Aquatic"})
    for i in range(5):
        rows.append({"url": f"u/e{i}", "title": f"e{i}", "discipline_primary": "Entomology"})
    return rows


def test_answers_accept_case_and_unique_prefix_but_reject_ambiguous():
    assert normalize_answer("WILDLIFE") == "Wildlife"
    assert normalize_answer("fish") == "Fisheries and Aquatic"
    assert normalize_answer("not") == "not_graduate"
    assert normalize_answer("e") is None  # Environmental vs Entomology: ambiguous
    assert normalize_answer("") is None
    assert normalize_answer("zzz") is None


def test_rare_classes_are_labeled_in_full_and_sample_is_reproducible():
    # A random draw would give a rare class 1-2 rows, too few to judge it.
    sample, meta = draw_sample(make_rows(), n=30, rare_below=10, seed=1)
    keys = [r["url"] for r, _ in sample]
    assert all(f"u/e{i}" in keys for i in range(5))
    assert len(sample) == 30 and len(set(keys)) == 30
    assert meta["strata"]["rare"] == {"population": 5, "sampled": 5}
    again, _ = draw_sample(make_rows(), n=30, rare_below=10, seed=1)
    other, _ = draw_sample(make_rows(), n=30, rare_below=10, seed=2)
    assert keys == [r["url"] for r, _ in again]
    assert keys != [r["url"] for r, _ in other]


def test_sample_csv_is_blind(tmp_path):
    positions = tmp_path / "pos.json"
    positions.write_text(json.dumps(make_rows()))
    args = Namespace(
        positions=positions, sample=tmp_path / "s.csv", key=tmp_path / "k.json",
        n=20, rare_below=10, seed=3,
    )
    cmd_sample(args)
    with open(args.sample, newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    assert reader.fieldnames == SAMPLE_COLUMNS
    text = args.sample.read_text()
    # The reviewer must not see the pipeline's label anywhere in the file.
    assert "discipline_primary" not in text and "predicted" not in text
    assert all(r["human_discipline"] == "" for r in rows)
    assert json.loads(args.key.read_text())["rows"]  # key kept separately


def test_stratified_accuracy_matches_hand_calculation():
    # rare: census of 2, 1 correct -> 0.5; common: 4 of 8 sampled, 3 correct -> 0.75
    # estimate = 0.2*0.5 + 0.8*0.75 = 0.70
    # variance = 0.8^2 * (1 - 4/8) * 0.75*0.25 / 3 = 0.02 (census adds none)
    est, half = stratified_accuracy(
        {"rare": [True, False], "common": [True, True, True, False]},
        {"rare": 2, "common": 8},
    )
    assert est == pytest.approx(0.70)
    assert half == pytest.approx(1.96 * 0.02**0.5)


def test_unclear_and_not_graduate_are_excluded_from_accuracy():
    key = {
        "meta": {"strata": {"common": {"population": 4, "sampled": 4}}},
        "rows": {
            "a": {"predicted": "Wildlife", "stratum": "common"},
            "b": {"predicted": "Wildlife", "stratum": "common"},
            "c": {"predicted": "Wildlife", "stratum": "common"},
            "d": {"predicted": "Wildlife", "stratum": "common"},
        },
    }
    result = score(key, {"a": "Wildlife", "b": "Fisheries and Aquatic",
                         "c": "unclear", "d": "not_graduate"})
    assert result["labeled"] == 2 and result["unclear"] == 1
    assert result["not_graduate"] == {"common": 1}
    assert result["accuracy"] == pytest.approx(0.5)
    assert result["top_confusions"] == [(("Wildlife", "Fisheries and Aquatic"), 1)]


def test_wilson_interval_brackets_the_proportion():
    lo, hi = wilson(9, 10)
    assert lo < 0.9 < hi and 0 <= lo and hi <= 1
    assert wilson(0, 0) == (0.0, 1.0)


def test_workbook_has_dropdown_limited_to_allowed_answers(tmp_path):
    # The dropdown is what keeps typos out of the human labels.
    openpyxl = pytest.importorskip("openpyxl")
    from discipline_validation import ANSWERS, write_workbook

    records = [{"position_key": f"k{i}", "title": f"t{i}"} for i in range(3)]
    path = tmp_path / "s.xlsx"
    write_workbook(records, path)

    wb = openpyxl.load_workbook(path)
    validation = wb["Label"].data_validations.dataValidation[0]
    assert validation.type == "list" and validation.showErrorMessage
    assert str(validation.sqref) == "H2:H4"
    assert [c.value for c in wb["Lists"]["A"]] == ANSWERS


def test_answers_round_trip_through_workbook(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    from discipline_validation import read_answers, write_workbook

    path = tmp_path / "s.xlsx"
    write_workbook([{"position_key": "k1", "title": "t"}, {"position_key": "k2"}], path)
    wb = openpyxl.load_workbook(path)
    wb["Label"]["H2"] = "Wildlife"
    wb.save(path)

    rows = read_answers(path)
    assert [r["human_discipline"] for r in rows] == ["Wildlife", ""]


def test_corrections_override_labels_and_null_excludes_row(tmp_path):
    from discipline_validation import apply_corrections

    path = tmp_path / "c.json"
    path.write_text(json.dumps({"corrections": {
        "a": {"label": "Wildlife", "reason": "herpetology"},
        "b": {"label": None, "reason": "pending"},
    }}))
    answers = {"a": "Other", "b": "Other", "c": "Other"}
    assert apply_corrections(answers, path) == (1, 1)
    assert answers == {"a": "Wildlife", "c": "Other"}
    assert apply_corrections(answers, tmp_path / "missing.json") == (0, 0)


def test_recheck_selects_only_changed_rows_the_reviewer_has_not_seen():
    # Re-labeling rows the reviewer already judged would waste their time and
    # re-labeling unchanged rows would measure nothing about the rule change.
    from discipline_validation import changed_rows

    rows = [{"url": u} for u in ("a", "b", "c", "d")]
    before = {"a": "Wildlife", "b": "Wildlife", "c": "Wildlife", "d": "Wildlife"}
    after = {"a": "Wildlife", "b": "Other", "c": "Other", "d": "Other"}
    picked = changed_rows(rows, before, after, already_labeled={"c"})
    assert [r["url"] for r in picked] == ["b", "d"]
