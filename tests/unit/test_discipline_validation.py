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


def test_gold_key_matches_the_retrainer_key_format():
    # A mismatch would make imported labels invisible to (or duplicated by) retraining.
    from discipline_validation import gold_key
    from retrain_discipline_model import position_key as retrain_key

    for row in (
        {"url": "HTTPS://Jobs.Example/View?id=1"},
        {"title": "T", "organization": "O", "location": "L", "published_date": "1/2/26"},
        {"title": "Only title", "published_date": "1/2/26"},
    ):
        assert gold_key(row) == retrain_key(row)


def test_human_labels_replace_machine_labels_and_are_counted():
    from discipline_validation import gold_key, merge_human_gold

    rows = {k: {"url": f"u/{k}", "title": k, "description": f"d-{k}"} for k in "abcd"}
    payload = {"labels": [
        {"position_key": gold_key(rows["a"]), "discipline": "Wildlife", "source": "auto_seed_high_confidence_v1", "description": ""},
        {"position_key": gold_key(rows["b"]), "discipline": "Wildlife", "source": "auto_seed_high_confidence_v1", "description": "kept"},
    ]}
    counts = merge_human_gold(
        payload,
        {"a": "Forestry and Habitat", "b": "Wildlife", "c": "Other", "zzz": "Wildlife"},
        rows,
        "2026-10-02",
    )
    assert counts == {"added": 1, "relabeled": 1, "confirmed": 1, "missing_row": 1}
    by_key = {item["position_key"]: item for item in payload["labels"]}
    relabeled = by_key[gold_key(rows["a"])]
    assert relabeled["discipline"] == "Forestry and Habitat"
    assert relabeled["source"] == "human_validation" and relabeled["description"] == "d-a"
    assert by_key[gold_key(rows["b"])]["description"] == "kept"
    assert by_key[gold_key(rows["c"])]["discipline"] == "Other"


def test_weekly_auto_seed_never_overwrites_a_human_label(tmp_path):
    # The workflow auto-seeds gold from the pipeline's own output every run;
    # human labels are only worth importing if that cannot clobber them.
    from retrain_discipline_model import position_key as retrain_key
    from retrain_discipline_model import seed_gold_from_positions

    def row(i, title):
        return {
            "url": f"u/{i}", "title": title, "organization": "Univ",
            "description": "wildlife mammal bird wildlife management wildlife ecology",
            "discipline_primary": "Wildlife", "grad_confidence": 0.9,
        }

    human_row = row(0, "Wildlife mammal bird ecology position")
    payload = {"version": 1, "labels": [{
        "position_key": retrain_key(human_row), "discipline": "Forestry and Habitat",
        "source": "human_validation", "title": human_row["title"],
    }]}
    others = [row(1, "Wildlife bird study"), row(2, "Wildlife mammal study")]
    added = seed_gold_from_positions(payload, tmp_path / "gold.json", [human_row] + others, 5, 0.5)

    assert added == 2  # the machine seeding did run, so this is not vacuous
    kept = [x for x in payload["labels"] if x["position_key"] == retrain_key(human_row)]
    assert len(kept) == 1
    assert kept[0]["discipline"] == "Forestry and Habitat"
    assert kept[0]["source"] == "human_validation"
