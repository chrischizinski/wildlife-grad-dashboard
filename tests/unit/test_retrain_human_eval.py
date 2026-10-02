"""Model quality must be judged on human labels, not on the rules' own output."""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from retrain_discipline_model import (  # noqa: E402
    evaluate_human_cv,
    human_gold_keys,
    promotion_decision,
)

VOCAB = {
    "Wildlife": "wildlife bird mammal avian predator",
    "Fisheries and Aquatic": "fish stream salmon aquatic river",
    "Forestry and Habitat": "forest timber silviculture woodland canopy",
}


def make_gold(human_per_class=12, machine_per_class=30, scramble_human=False):
    texts, labels, human_idx = [], [], []
    classes = list(VOCAB)
    rng = random.Random(0)
    for cls in classes:
        for i in range(machine_per_class):
            texts.append(f"{VOCAB[cls]} study {i}")
            labels.append(cls)
    for ci, cls in enumerate(classes):
        for i in range(human_per_class):
            texts.append(f"{VOCAB[cls]} project {i}")
            labels.append(rng.choice(classes) if scramble_human else cls)
            human_idx.append(len(texts) - 1)
    return texts, labels, human_idx


def run(**kw):
    texts, labels, human_idx = make_gold(**kw)
    return evaluate_human_cv(texts, labels, human_idx, [], [], 0.5)


def test_skipped_when_there_are_too_few_human_labels():
    texts, labels, human_idx = make_gold(human_per_class=5)  # 15 < 30
    assert evaluate_human_cv(texts, labels, human_idx, [], [], 0.5) is None


def test_every_human_row_is_predicted_exactly_once_by_a_model_that_never_saw_it():
    result = run()
    assert result["n"] == 36 and result["folds"] == 5
    assert result["accuracy"] > 0.9  # separable data: a sound pipeline scores high


def test_score_is_against_the_human_labels_not_the_text_or_machine_labels():
    # Human labels are unrelated to what the text and machine labels imply (and
    # not learnable), so a metric that scored against the text would stay high.
    assert run(scramble_human=True)["accuracy"] < 0.6


def test_only_person_assigned_labels_count_as_human():
    payload = {"labels": [
        {"position_key": "a", "source": "human_validation"},
        {"position_key": "b", "source": "auto_seed_high_confidence_v1"},
        {"position_key": "c", "source": "bootstrap_ml_training_data"},
    ]}
    assert human_gold_keys(payload) == {"a"}


def gate(new, old):
    return promotion_decision(new, old, 0.005, 0.01, force_promote=False)


def test_first_human_scored_candidate_replaces_a_model_with_no_human_score():
    # The old model was only ever scored against machine labels; its stored
    # numbers are not comparable, so it must not block the first honest candidate.
    new = {"accuracy": 0.7, "macro_f1": 0.6, "human_cv": {"accuracy": 0.7, "macro_f1": 0.6}}
    old = {"accuracy": 0.9, "macro_f1": 0.9}
    assert gate(new, old) == (True, "evaluation_basis_changed_to_human_labels")


def test_once_both_have_human_scores_candidates_must_beat_the_human_score():
    old = {"accuracy": 0.5, "macro_f1": 0.5, "human_cv": {"accuracy": 0.7, "macro_f1": 0.7}}
    worse = {"accuracy": 0.99, "macro_f1": 0.99, "human_cv": {"accuracy": 0.6, "macro_f1": 0.6}}
    better = {"accuracy": 0.1, "macro_f1": 0.1, "human_cv": {"accuracy": 0.8, "macro_f1": 0.8}}
    assert gate(worse, old)[0] is False  # machine-label score no longer decides
    assert gate(better, old) == (True, "macro_f1_improved")


def test_without_human_scores_the_old_rule_still_applies():
    assert gate({"accuracy": 0.7, "macro_f1": 0.7}, {"accuracy": 0.7, "macro_f1": 0.7}) == (False, "validation_not_improved")
